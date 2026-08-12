import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from tests.user_home_test_case import IsolatedUserHomeTestCase
from vibeagent.agent_result import AgentResult
from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.cli_args import parse_args
from vibeagent.cli_one_shot_code import run_one_shot_code
from vibeagent.cli_output_mode import CliOutputMode
from vibeagent.cli_verbose_output import MAX_VERBOSE_DETAIL_CHARS, VerboseTranscriptRenderer
from vibeagent.config import ExecutionConfig
from vibeagent.interactive_background import create_interactive_background_request
from vibeagent.workspace_core import create_local_workspace
from vibeagent.workspace_view_mode import resolve_verbose_mode


class WorkspaceViewModeTests(IsolatedUserHomeTestCase):
    def test_setting_precedence_and_explicit_override(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-view-mode-") as base:
            root = Path(base)
            project = root / ".claude" / "settings.json"
            local = root / ".claude" / "settings.local.json"
            project.parent.mkdir(parents=True)
            project.write_text('{"viewMode":"verbose"}', encoding="utf-8")
            local.write_text('{"viewMode":"focus"}', encoding="utf-8")
            workspace = create_local_workspace(root, "view-mode")

            self.assertFalse(resolve_verbose_mode(workspace))
            self.assertTrue(resolve_verbose_mode(workspace, explicit=True))
            local.write_text('{"viewMode":"verbose"}', encoding="utf-8")
            self.assertTrue(resolve_verbose_mode(workspace))
            self.assertFalse(
                resolve_verbose_mode(
                    create_local_workspace(root, "safe-view-mode", safe_mode=True)
                )
            )

    def test_invalid_setting_fails_with_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-view-mode-") as base:
            root = Path(base)
            settings = root / ".claude" / "settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text('{"viewMode":"wide"}', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, r"\.claude/settings\.json viewMode"):
                resolve_verbose_mode(create_local_workspace(root, "view-mode"))


class VerboseTranscriptRendererTests(unittest.TestCase):
    def test_renders_bounded_redacted_turns_and_tool_events(self) -> None:
        output = io.StringIO()
        renderer = VerboseTranscriptRenderer(output, show_model_text=True)
        renderer.observe(
            Path("/tmp/session"),
            {
                "type": "model",
                "iteration": 1,
                "content": [{"type": "text", "text": "Inspecting the project."}],
            },
        )
        renderer.observe(
            Path("/tmp/session"),
            {
                "type": "tool_call",
                "iteration": 1,
                "name": "read_file",
                "input": {"path": "README.md", "api_key": "secret-value", "query": "x" * 5000},
            },
        )
        renderer.observe(
            Path("/tmp/session"),
            {
                "type": "tool_result",
                "iteration": 1,
                "name": "read_file",
                "result": {"kind": "read_file", "ok": True},
            },
        )

        text = output.getvalue()
        self.assertIn("[verbose] turn 1 assistant", text)
        self.assertIn("[verbose] turn 1 tool read_file", text)
        self.assertIn("[verbose] turn 1 result read_file", text)
        self.assertNotIn("secret-value", text)
        self.assertIn("[truncated", text)
        self.assertLess(len(max(text.splitlines(), key=len)), MAX_VERBOSE_DETAIL_CHARS + 100)

    def test_streaming_mode_does_not_repeat_model_text(self) -> None:
        output = io.StringIO()
        renderer = VerboseTranscriptRenderer(output, show_model_text=False)

        renderer.observe(
            Path("/tmp/session"),
            {"type": "model", "iteration": 1, "content": [{"type": "text", "text": "Done."}]},
        )

        self.assertEqual(output.getvalue(), "")

    def test_one_shot_verbose_writes_transcript_to_stderr(self) -> None:
        stderr = io.StringIO()

        def run_agent(_task, **kwargs):
            workspace = kwargs["workspace"]
            append_session_event(
                workspace.session_dir,
                "model",
                {"iteration": 1, "content": [{"type": "text", "text": "Working."}]},
            )
            append_session_event(
                workspace.session_dir,
                "tool_call",
                {"iteration": 1, "id": "1", "name": "read_file", "input": {"path": "README.md"}},
            )
            append_session_event(
                workspace.session_dir,
                "tool_result",
                {"iteration": 1, "id": "1", "name": "read_file", "result": {"ok": True}},
            )
            return AgentResult(True, "done", workspace.root, workspace.run_id, 1, [], [])

        with tempfile.TemporaryDirectory(prefix="vibeagent-verbose-one-shot-") as base, (
            patch("vibeagent.cli_one_shot_code.emit_one_shot_code_payload")
        ), patch("vibeagent.cli_one_shot_code.run_session_end_hooks"), patch(
            "vibeagent.cli_one_shot_code.create_peer_runtime", return_value=None
        ), redirect_stderr(stderr):
            exit_code, _ = run_one_shot_code(
                "inspect",
                project_root=Path(base),
                execution_config=ExecutionConfig(),
                provider_env={},
                approval_policy="ask",
                trust_project_permissions=False,
                permission_overrides=None,
                resolved_mcp_config_paths=(),
                strict_mcp_config=False,
                verbose=True,
                output_mode=CliOutputMode(format="text", machine=False, stream_json=False),
                output_json=False,
                print_mode=True,
                elapsed_ms=1,
                stream=None,
                input_prior_context=None,
                system_prompt=None,
                append_system_prompt=None,
                task_metadata=None,
                resume_arg=None,
                compact_arg=None,
                auto_compact=False,
                create_chat_client_func=lambda _env: object(),
                run_agent_func=run_agent,
                get_resume_context_func=lambda *args, **kwargs: (None, None, "unused"),
                get_compact_context_func=lambda *args, **kwargs: (None, None, "unused"),
            )

        self.assertEqual(exit_code, 0)
        self.assertIn("[verbose] turn 1 assistant", stderr.getvalue())
        self.assertIn("[verbose] turn 1 tool read_file", stderr.getvalue())

    def test_parser_and_background_handoff_preserve_explicit_flag(self) -> None:
        self.assertTrue(parse_args(["--verbose", "inspect"]).verbose)
        request = create_interactive_background_request(
            Path("/project"),
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
            verbose=True,
        )
        self.assertIn("--verbose", request.argv)


if __name__ == "__main__":
    unittest.main()
