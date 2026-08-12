import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli_interactive import run_interactive_loop
from vibeagent.cli import run_interactive
from vibeagent.cli_args import parse_args
from vibeagent.cli_startup_context import resolve_interactive_startup_context
from vibeagent.dynamic_agent_profiles import parse_dynamic_agent_profiles
from vibeagent.interactive_background import (
    DEFAULT_BACKGROUND_PROMPT,
    InteractiveBackgroundRequest,
    create_interactive_background_request,
    serialize_dynamic_agent_profiles,
)


class InteractiveBackgroundTests(unittest.TestCase):
    def test_request_preserves_session_options_and_separates_prompt(self) -> None:
        profiles = parse_dynamic_agent_profiles(
            '{"tester":{"description":"Tests code","prompt":"Run focused tests","mode":"code"}}'
        )
        request = create_interactive_background_request(
            Path("."),
            "run-1",
            "--model is task text",
            approval_policy="allow",
            model="model-1",
            agent="main",
            dynamic_agent_profiles=profiles,
            effort="high",
            autocompact_tokens=200_000,
            system_prompt="system",
            append_system_prompt="append",
            additional_directories=(Path("shared"),),
            anthropic_betas=("interleaved-thinking", "files-api-2025-04-14"),
        )

        self.assertEqual(request.argv[-2:], ("--", "--model is task text"))
        self.assertIn("--resume", request.argv)
        self.assertIn("run-1", request.argv)
        self.assertIn("--approval", request.argv)
        self.assertIn("allow", request.argv)
        self.assertIn("--agents", request.argv)
        self.assertEqual(request.argv.count("--betas"), 2)
        self.assertIn("interleaved-thinking", request.argv)
        self.assertEqual(
            parse_dynamic_agent_profiles(serialize_dynamic_agent_profiles(profiles)),
            profiles,
        )

    def test_interactive_bg_raises_handoff_for_active_session(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-interactive-bg-") as base:
            root = Path(base)
            stdout = io.StringIO()
            previous = Path.cwd()
            try:
                with (
                    patch("builtins.input", return_value="/bg finish the tests"),
                    patch("vibeagent.cli_interactive.prompt_project_permission_trust", return_value=False),
                    redirect_stdout(stdout),
                ):
                    os.chdir(root)
                    with self.assertRaises(InteractiveBackgroundRequest) as raised:
                        run_interactive_loop(
                            command_namespace={},
                            initial_resume_run_id="run-1",
                            initial_attached_background_agent_id="0123456789ab",
                            initial_provider_env_overrides=(
                                ("ANTHROPIC_BETA", "interleaved-thinking"),
                            ),
                        )
            finally:
                os.chdir(previous)

        self.assertEqual(raised.exception.prompt, "finish the tests")
        self.assertEqual(raised.exception.run_id, "run-1")
        self.assertEqual(raised.exception.attached_agent_id, "0123456789ab")
        self.assertIn("--betas", raised.exception.argv)
        self.assertIn("interleaved-thinking", raised.exception.argv)

    def test_interactive_bg_without_session_stays_foreground(self) -> None:
        stdout = io.StringIO()
        with (
            patch("builtins.input", side_effect=["/bg", "/exit"]),
            patch("vibeagent.cli_interactive.prompt_project_permission_trust", return_value=False),
            redirect_stdout(stdout),
        ):
            code = run_interactive_loop(command_namespace={})

        self.assertEqual(code, 0)
        self.assertIn("requires an active coding session", stdout.getvalue())

    def test_default_prompt_is_bounded_continuation(self) -> None:
        request = create_interactive_background_request(
            Path("."),
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
        )

        self.assertEqual(request.prompt, DEFAULT_BACKGROUND_PROMPT)

    def test_request_preserves_bypass_permission_availability(self) -> None:
        request = create_interactive_background_request(
            Path("."),
            "run-1",
            None,
            approval_policy="plan",
            model=None,
            agent=None,
            dynamic_agent_profiles=(),
            effort=None,
            autocompact_tokens=None,
            system_prompt=None,
            append_system_prompt=None,
            additional_directories=(),
            bypass_permissions_available=True,
        )

        self.assertIn("--allow-dangerously-skip-permissions", request.argv)

    def test_normal_interactive_launches_new_background_agent(self) -> None:
        request = create_interactive_background_request(
            Path("."),
            "run-1",
            "finish tests",
            approval_policy="ask",
            model=None,
            agent=None,
            dynamic_agent_profiles=(),
            effort=None,
            autocompact_tokens=None,
            system_prompt=None,
            append_system_prompt=None,
            additional_directories=(),
        )
        view = type(
            "View",
            (),
            {
                "record": type(
                    "Record",
                    (),
                    {
                        "id": "0123456789ab",
                        "session_name": "run-1",
                    },
                )()
            },
        )()

        with (
            patch("vibeagent.cli.run_interactive_loop", side_effect=request),
            patch(
                "vibeagent.cli.launch_interactive_background_request",
                return_value=view,
            ) as launch,
            redirect_stdout(io.StringIO()),
        ):
            code = run_interactive()

        self.assertEqual(code, 0)
        launch.assert_called_once()
        self.assertIs(launch.call_args.args[0], request)

    def test_startup_context_preserves_model_and_approval(self) -> None:
        args = parse_args(["--model-name", "model-1", "--approval", "allow"])

        context = resolve_interactive_startup_context(args, Path.cwd())

        self.assertEqual(context.model, "model-1")
        self.assertEqual(context.approval, "allow")


if __name__ == "__main__":
    unittest.main()
