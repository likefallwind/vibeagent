import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from vibeagent.agent import AgentResult
from vibeagent.cli import main
from vibeagent.types import ApprovalRequest, AssistantResponse, ChatMessage
from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.session_branching import read_session_branch_info
from vibeagent.session_conversation import checkpoint_session_conversation
from vibeagent.workspace_core import create_run_workspace


class CliInteractiveStateTests(unittest.TestCase):
    def test_interactive_brief_displays_update_and_continues_to_final_message(self) -> None:
        class BriefClient:
            def __init__(self) -> None:
                self.calls = 0

            def complete(self, messages, tools=None, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    self.assert_tools = {str(tool["name"]) for tool in tools or []}
                    return AssistantResponse(
                        content=[{
                            "type": "tool_call",
                            "id": "brief-1",
                            "name": "SendUserMessage",
                            "input": {"message": "Focused checks passed; running full suite."},
                        }],
                        raw={},
                    )
                return AssistantResponse(
                    content=[{"type": "text", "text": "Full suite passed."}],
                    raw={},
                )

        client = BriefClient()
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-brief-") as base:
            stdout = io.StringIO()
            with (
                patch("builtins.input", side_effect=["inspect", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=client),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--brief", "--cwd", base])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("SendUserMessage", client.assert_tools)
        self.assertIn("Agent update: Focused checks passed; running full suite.", output)
        self.assertIn("Full suite passed.", output)

    def test_interactive_code_streams_text_without_reprinting_final_message(self) -> None:
        class StreamingClient:
            def complete(self, *args, **kwargs):
                raise AssertionError("interactive turns should use complete_stream")

            def complete_stream(self, messages, *, on_event, **kwargs):
                on_event({"type": "message_start"})
                on_event(
                    {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "streamed result"}}
                )
                on_event({"type": "message_stop"})
                return AssistantResponse(
                    content=[{"type": "text", "text": "streamed result"}],
                    raw={},
                )

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-stream-code-") as base:
            root = Path(base)

            stdout = io.StringIO()
            with (
                patch("builtins.input", side_effect=["inspect", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=StreamingClient()),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", str(root)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue().count("streamed result"), 1)

    def test_interactive_chat_streams_text_without_reprinting_response(self) -> None:
        class StreamingClient:
            def complete(self, *args, **kwargs):
                raise AssertionError("interactive turns should use complete_stream")

            def complete_stream(self, messages, *, on_event, **kwargs):
                on_event({"type": "message_start"})
                on_event(
                    {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "streamed chat"}}
                )
                on_event({"type": "message_stop"})
                return AssistantResponse(
                    content=[{"type": "text", "text": "streamed chat"}],
                    raw={},
                )

        stdout = io.StringIO()
        with (
            patch("builtins.input", side_effect=["/chat hello", "/exit"]),
            patch("vibeagent.cli.create_chat_client", return_value=StreamingClient()),
            redirect_stdout(stdout),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue().count("streamed chat"), 1)

    def test_explicit_resume_restores_persisted_conversation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-resume-conversation-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, run_id="run-1")
            checkpoint_session_conversation(
                workspace,
                [
                    ChatMessage(role="user", content="User task:\nfirst"),
                    ChatMessage(role="assistant", content="durable marker"),
                ],
                "first",
            )
            calls: list[dict[str, object]] = []

            def run_agent(task, **kwargs):
                calls.append(kwargs)
                return AgentResult(True, "done", root, kwargs["workspace"].run_id, 1, [], [])

            with (
                patch("builtins.input", side_effect=["/resume run-1", "continue", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", side_effect=run_agent),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=[
                        ("run-1", "source context", "loaded"),
                        ("run-1", "next context", "loaded"),
                    ],
                ),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", str(root)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls[0]["workspace"].run_id, "run-1")
        self.assertIsNone(calls[0]["task_source_run_id"])
        self.assertEqual(calls[0]["prior_messages"][-1].content, "durable marker")

    def test_clear_starts_new_session_without_in_memory_conversation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-clear-") as base:
            root = Path(base)
            calls: list[dict[str, object]] = []

            def run_agent(task, **kwargs):
                calls.append(kwargs)
                workspace = kwargs["workspace"] or create_run_workspace(root)
                return AgentResult(
                    True,
                    "done",
                    root,
                    workspace.run_id,
                    1,
                    [],
                    [],
                    conversation=[ChatMessage(role="assistant", content=f"memory: {task}")],
                )

            with (
                patch("builtins.input", side_effect=["first task", "/clear", "fresh task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", side_effect=run_agent),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=lambda run_id, **kwargs: (run_id, "context", "loaded"),
                ),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", str(root)])

        self.assertEqual(exit_code, 0)
        self.assertIsNone(calls[0]["prior_messages"])
        self.assertIsNone(calls[1]["prior_messages"])
        self.assertIsNone(calls[1]["workspace"])

    def test_main_interactive_reuses_session_workspace_across_code_turns(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-session-") as base:
            root = Path(base)
            calls: list[dict[str, object]] = []
            created_run_ids: list[str] = []

            def run_agent(task, **kwargs):
                calls.append(kwargs)
                workspace = kwargs["workspace"] or create_run_workspace(root)
                if kwargs["workspace"] is None:
                    created_run_ids.append(workspace.run_id)
                return AgentResult(
                    True,
                    "done",
                    root,
                    workspace.run_id,
                    1,
                    [],
                    [],
                    conversation=[
                        ChatMessage(role="system", content="system"),
                        ChatMessage(role="user", content=task),
                        ChatMessage(role="assistant", content=f"done: {task}"),
                    ],
                )

            def get_context(run_id, **kwargs):
                return run_id, f"context for {run_id}", "loaded"

            with (
                patch("builtins.input", side_effect=["first task", "second task", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", side_effect=run_agent),
                patch("vibeagent.cli.get_resume_context", side_effect=get_context),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", str(root)])

        self.assertEqual(exit_code, 0)
        self.assertIsNone(calls[0]["workspace"])
        second_workspace = calls[1]["workspace"]
        self.assertIsNotNone(second_workspace)
        self.assertEqual(second_workspace.run_id, created_run_ids[0])
        self.assertIsNone(calls[1]["task_source_run_id"])
        self.assertEqual(calls[1]["prior_messages"][-1].content, "done: first task")

    def test_main_interactive_agent_profile_is_forwarded_to_code_turns(self) -> None:
        result = AgentResult(
            success=True,
            message="done",
            run_dir=Path(tempfile.gettempdir()),
            run_id="test-run",
            iterations=1,
            observations=[],
            steps=[],
        )
        run_agent = Mock(return_value=result)

        with (
            patch("builtins.input", side_effect=["inspect code", "/exit"]),
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_agent", run_agent),
            redirect_stdout(io.StringIO()),
        ):
            exit_code = main(["--agent", "reviewer"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["agent"], "reviewer")

    def test_main_interactive_dynamic_agents_are_forwarded_to_each_code_turn(self) -> None:
        result = AgentResult(
            success=True,
            message="done",
            run_dir=Path(tempfile.gettempdir()),
            run_id="test-run",
            iterations=1,
            observations=[],
            steps=[],
        )
        run_agent = Mock(return_value=result)
        definitions = json.dumps(
            {
                "reviewer": {
                    "description": "Reviews code",
                    "prompt": "Inspect evidence only",
                    "tools": ["Read"],
                }
            }
        )

        with (
            patch("builtins.input", side_effect=["inspect code", "/exit"]),
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_agent", run_agent),
            redirect_stdout(io.StringIO()),
        ):
            exit_code = main(["--agents", definitions])

        self.assertEqual(exit_code, 0)
        profiles = run_agent.call_args.kwargs["dynamic_agent_profiles"]
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0].name, "reviewer")

    def test_main_interactive_prompt_files_are_resolved_before_changing_cwd(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            project = root / "project"
            project.mkdir()
            (root / "system.txt").write_text("System from file.", encoding="utf-8")
            (root / "append.txt").write_text("Append from file.", encoding="utf-8")
            result = AgentResult(
                success=True,
                message="done",
                run_dir=project,
                run_id="test-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)
            previous_cwd = Path.cwd()
            os.chdir(root)
            try:
                with (
                    patch("builtins.input", side_effect=["inspect code", "/exit"]),
                    patch("vibeagent.cli.create_chat_client", return_value=object()),
                    patch("vibeagent.cli.run_agent", run_agent),
                    redirect_stdout(io.StringIO()),
                ):
                    exit_code = main(
                        [
                            "--cwd",
                            str(project),
                            "--system-prompt-file",
                            "system.txt",
                            "--append-system-prompt-file",
                            "append.txt",
                        ]
                    )
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["system_prompt"], "System from file.")
        self.assertEqual(run_agent.call_args.kwargs["append_system_prompt"], "Append from file.")

    def test_main_interactive_additional_directory_is_resolved_before_changing_cwd(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            project = root / "project"
            shared = root / "shared"
            project.mkdir()
            shared.mkdir()
            result = AgentResult(
                success=True,
                message="done",
                run_dir=project,
                run_id="test-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)
            previous_cwd = Path.cwd()
            os.chdir(root)
            try:
                with (
                    patch("builtins.input", side_effect=["inspect shared", "/exit"]),
                    patch("vibeagent.cli.create_chat_client", return_value=object()),
                    patch("vibeagent.cli.run_agent", run_agent),
                    redirect_stdout(io.StringIO()),
                ):
                    exit_code = main(["--cwd", str(project), "--add-dir", "shared"])
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["additional_directories"], (shared.resolve(),))

    def test_main_interactive_add_dir_changes_following_code_turns(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            project = root / "project"
            shared = root / "shared"
            project.mkdir()
            shared.mkdir()
            result = AgentResult(
                success=True,
                message="done",
                run_dir=project,
                run_id="test-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)
            stdout = io.StringIO()

            with (
                patch(
                    "builtins.input",
                    side_effect=[
                        "/add-dir ../shared",
                        "inspect shared",
                        "/add-dir remove ../shared",
                        "inspect project",
                        "/exit",
                    ],
                ),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", str(project)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args_list[0].kwargs["additional_directories"], (shared.resolve(),))
        self.assertEqual(run_agent.call_args_list[1].kwargs["additional_directories"], ())
        self.assertIn("Added working directory", stdout.getvalue())
        self.assertIn("Removed additional working directory", stdout.getvalue())

    def test_main_interactive_cd_switches_project_and_preserves_conversation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-cd-") as base:
            root = Path(base)
            first = root / "first"
            second = root / "second project"
            first.mkdir()
            second.mkdir()
            calls: list[tuple[str, Path, dict[str, object]]] = []

            def run_agent(task, **kwargs):
                current_root = Path.cwd().resolve()
                calls.append((task, current_root, kwargs))
                workspace = kwargs["workspace"] or create_run_workspace(current_root, "source-run")
                return AgentResult(
                    True,
                    "done",
                    current_root,
                    workspace.run_id,
                    1,
                    [],
                    [],
                    conversation=[ChatMessage(role="assistant", content=f"memory: {task}")],
                )

            stdout = io.StringIO()
            create_client = Mock(return_value=object())
            with (
                patch(
                    "builtins.input",
                    side_effect=["first task", '/cd "../second project"', "second task", "/exit"],
                ),
                patch("vibeagent.cli.create_chat_client", create_client),
                patch("vibeagent.cli.run_agent", side_effect=run_agent),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=lambda run_id, **kwargs: (run_id, f"context for {run_id}", "loaded"),
                ),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", str(first)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls[0][0:2], ("first task", first.resolve()))
        self.assertEqual(calls[1][0:2], ("second task", second.resolve()))
        self.assertEqual(calls[1][2]["workspace"].root, second.resolve())
        self.assertEqual(calls[1][2]["task_source_run_id"], "source-run")
        self.assertEqual(calls[1][2]["prior_messages"][-1].content, "memory: first task")
        self.assertEqual(create_client.call_count, 2)
        self.assertIn("Changed project directory", stdout.getvalue())
        self.assertIn("Conversation preserved in new session", stdout.getvalue())

    def test_main_interactive_cd_failure_keeps_current_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-cd-failure-") as base:
            project = Path(base) / "project"
            project.mkdir()
            roots: list[Path] = []

            def run_agent(task, **kwargs):
                current_root = Path.cwd().resolve()
                roots.append(current_root)
                workspace = kwargs["workspace"] or create_run_workspace(current_root, "current-run")
                return AgentResult(True, "done", current_root, workspace.run_id, 1, [], [])

            stdout = io.StringIO()
            with (
                patch("builtins.input", side_effect=["/cd missing", "inspect", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", side_effect=run_agent),
                patch(
                    "vibeagent.cli.get_resume_context",
                    side_effect=lambda run_id, **kwargs: (run_id, "context", "loaded"),
                ),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", str(project)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(roots, [project.resolve()])
        self.assertIn("Cannot change directory", stdout.getvalue())

    def test_main_interactive_add_dir_schedules_only_added_directory_hook(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-directory-hook-") as base:
            project = Path(base) / "project"
            shared = Path(base) / "shared"
            project.mkdir()
            shared.mkdir()
            result = AgentResult(True, "done", project, "test-run", 1, [], [])

            with (
                patch(
                    "builtins.input",
                    side_effect=[
                        "/add-dir ../shared",
                        "/add-dir remove ../shared",
                        "/exit",
                    ],
                ),
                patch("vibeagent.cli_interactive.schedule_directory_added_hooks") as schedule,
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", str(project)])

        self.assertEqual(exit_code, 0)
        schedule.assert_called_once()
        self.assertEqual(schedule.call_args.args[1], shared.resolve())
        self.assertEqual(schedule.call_args.args[2], "slash_command")
        self.assertIn(shared.resolve(), schedule.call_args.args[0].additional_roots)

    def test_directory_added_system_message_enters_next_code_task(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-directory-context-") as base:
            project = Path(base) / "project"
            project.mkdir()
            result = AgentResult(True, "done", project, "test-run", 1, [], [])
            run_agent = Mock(return_value=result)
            with (
                patch("builtins.input", side_effect=["inspect", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                patch(
                    "vibeagent.cli_interactive.collect_directory_added_turn_context",
                    return_value=("DirectoryAdded hook context:\nprepared context", ()),
                ),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", str(project)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.args[0], "inspect")
        self.assertIn(
            "DirectoryAdded hook context:\nprepared context",
            run_agent.call_args.kwargs["append_system_prompt"],
        )

    def test_main_interactive_resume_restores_session_additional_directories(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base) / "project"
            shared = Path(base) / "shared"
            root.mkdir()
            shared.mkdir()
            append_session_event(
                root / ".vibeagent" / "sessions" / "run-old",
                "task",
                {"additional_directories": [str(shared.resolve())]},
            )
            result = AgentResult(True, "done", root, "run-new", 1, [], [])
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["/resume run-old", "continue", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                patch(
                    "vibeagent.cli.get_resume_context",
                    return_value=("run-old", "previous context", "Resume loaded."),
                ),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", str(root)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["additional_directories"], (shared.resolve(),))

    def test_main_interactive_branch_runs_next_turn_in_new_session(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-branch-") as base:
            root = Path(base)
            source_dir = root / ".vibeagent" / "sessions" / "source-run"
            append_session_event(source_dir, "task", {"task": "source task"})
            source_events = source_dir.joinpath("events.jsonl").read_bytes()
            calls: list[dict[str, object]] = []

            def run_agent(task, **kwargs):
                calls.append(kwargs)
                workspace = kwargs["workspace"]
                return AgentResult(True, "done", root, workspace.run_id, 1, [], [])

            def get_context(run_id, project_root=root, **kwargs):
                selected = run_id or "source-run"
                return selected, f"context for {selected}", f"Loaded {selected}."

            with (
                patch("builtins.input", side_effect=["/branch try-oauth", "implement alternative", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", side_effect=run_agent),
                patch("vibeagent.cli.get_resume_context", side_effect=get_context),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", str(root), "--resume", "source-run"])

            branch_workspace = calls[0]["workspace"]
            branch_info = read_session_branch_info(root, branch_workspace.run_id)

            self.assertEqual(exit_code, 0)
            self.assertNotEqual(branch_workspace.run_id, "source-run")
            self.assertEqual(calls[0]["task_source_run_id"], "source-run")
            self.assertEqual(branch_info.source_run_id, "source-run")  # type: ignore[union-attr]
            self.assertEqual(branch_info.name, "try-oauth")  # type: ignore[union-attr]
            self.assertEqual(source_dir.joinpath("events.jsonl").read_bytes(), source_events)

    def test_main_interactive_rewind_runs_next_turn_in_new_session(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-rewind-") as base:
            root = Path(base)
            source_dir = root / ".vibeagent" / "sessions" / "source-run"
            append_session_event(source_dir, "task", {"task": "before checkpoint"})
            checkpoint_id = "2026-08-10T00-00-00-000Z-rewind01"
            checkpoint_dir = root / ".vibeagent" / "checkpoints" / checkpoint_id
            checkpoint_dir.mkdir(parents=True)
            checkpoint_dir.joinpath("metadata.json").write_text(
                json.dumps(
                    {
                        "id": checkpoint_id,
                        "created_at": "2026-08-10T00:00:00Z",
                        "head": "abc123",
                        "session_run_id": "source-run",
                        "session_event_line": 1,
                    }
                ),
                encoding="utf-8",
            )
            append_session_event(source_dir, "task", {"task": "after checkpoint"})
            source_events = source_dir.joinpath("events.jsonl").read_bytes()
            calls: list[dict[str, object]] = []

            def run_agent(task, **kwargs):
                calls.append(kwargs)
                workspace = kwargs["workspace"]
                return AgentResult(True, "done", root, workspace.run_id, 1, [], [])

            def get_context(run_id, project_root=root, **kwargs):
                selected = run_id or "source-run"
                return selected, f"context for {selected}", f"Loaded {selected}."

            stdout = io.StringIO()
            with (
                patch(
                    "builtins.input",
                    side_effect=[f"/rewind {checkpoint_id} conversation", "continue safely", "/exit"],
                ),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", side_effect=run_agent),
                patch("vibeagent.cli.get_resume_context", side_effect=get_context),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", str(root), "--resume", "source-run"])

            rewound_workspace = calls[0]["workspace"]
            self.assertEqual(exit_code, 0)
            self.assertNotEqual(rewound_workspace.run_id, "source-run")
            self.assertIsNone(calls[0]["task_source_run_id"])
            self.assertEqual(calls[0]["prior_context"], f"context for {rewound_workspace.run_id}")
            self.assertEqual(source_dir.joinpath("events.jsonl").read_bytes(), source_events)
            self.assertIn("Rewound conversation", stdout.getvalue())

    def test_main_updates_approval_policy_and_passes_handler_to_agent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="test-run",
                iterations=1,
                observations=[],
                steps=[],
            )
            stdout = io.StringIO()
            run_agent = Mock(return_value=result)

            with (
                patch("builtins.input", side_effect=["/approval allow", "write file", "/approval deny", "run command", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("Approval policy: allow", output)
        self.assertIn("Approval policy: deny", output)
        first_handler = run_agent.call_args_list[0].kwargs["approval_handler"]
        second_handler = run_agent.call_args_list[1].kwargs["approval_handler"]
        self.assertEqual(run_agent.call_args_list[0].kwargs["approval_policy"], "allow")
        self.assertEqual(run_agent.call_args_list[1].kwargs["approval_policy"], "deny")
        request = ApprovalRequest(action_type="write_file", target="note.txt", risk="write")
        self.assertTrue(first_handler(request).approved)
        self.assertFalse(second_handler(request).approved)

    def test_agent_plan_approval_updates_following_interactive_turn(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            result = AgentResult(
                success=True,
                message="done",
                run_dir=Path(base),
                run_id="test-run",
                iterations=1,
                observations=[],
                steps=[],
                approval_policy="allow",
            )
            run_agent = Mock(return_value=result)

            with (
                patch(
                    "builtins.input",
                    side_effect=["/approval plan", "plan and implement", "continue", "/exit"],
                ),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            [call.kwargs["approval_policy"] for call in run_agent.call_args_list],
            ["plan", "allow"],
        )

    def test_main_interactive_system_prompt_commands_affect_code_and_chat_turns(self) -> None:
        result = AgentResult(
            success=True,
            message="done",
            run_dir=Path(tempfile.gettempdir()),
            run_id="test-run",
            iterations=1,
            observations=[],
            steps=[],
        )
        stdout = io.StringIO()
        run_agent = Mock(return_value=result)
        run_chat = Mock(return_value="chat response")

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/system-prompt You are a release engineer.",
                    "/append-system-prompt Prefer focused tests.",
                    "inspect code",
                    "/chat explain",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_agent", run_agent),
            patch("vibeagent.cli.run_chat", run_chat),
            redirect_stdout(stdout),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.kwargs["system_prompt"], "You are a release engineer.")
        self.assertEqual(run_agent.call_args.kwargs["append_system_prompt"], "Prefer focused tests.")
        self.assertEqual(run_chat.call_args.kwargs["system_prompt"], "You are a release engineer.")
        self.assertEqual(run_chat.call_args.kwargs["append_system_prompt"], "Prefer focused tests.")
        output = stdout.getvalue()
        self.assertIn("System prompt set", output)
        self.assertIn("Appended system prompt set", output)

    def test_main_interactive_system_prompt_status_and_clear(self) -> None:
        result = AgentResult(
            success=True,
            message="done",
            run_dir=Path(tempfile.gettempdir()),
            run_id="test-run",
            iterations=1,
            observations=[],
            steps=[],
        )
        stdout = io.StringIO()
        run_agent = Mock(return_value=result)

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/system-prompt You are terse.",
                    "/append-system-prompt Prefer focused tests.",
                    "/status",
                    "/system-prompt off",
                    "/append-system-prompt off",
                    "inspect code",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_agent", run_agent),
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("systemPrompt: custom", output)
        self.assertIn("appendSystemPrompt: set", output)
        self.assertIn("System prompt cleared.", output)
        self.assertIn("Appended system prompt cleared.", output)
        self.assertIsNone(run_agent.call_args.kwargs["system_prompt"])
        self.assertIsNone(run_agent.call_args.kwargs["append_system_prompt"])

    def test_main_interactive_task_keyboard_interrupt_returns_to_prompt(self) -> None:
        stdout = io.StringIO()

        with (
            patch("builtins.input", side_effect=["write file", "/exit"]),
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_agent", side_effect=KeyboardInterrupt) as run_agent,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("Interrupted.", output)
        self.assertNotIn("Error:", output)
        self.assertEqual(run_agent.call_count, 1)


if __name__ == "__main__":
    unittest.main()
