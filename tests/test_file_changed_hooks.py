from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from vibeagent.agent import run_agent
from vibeagent.agent_execution_support import execute_action_safely
from vibeagent.agent_hook_results import HookRunResult
from vibeagent.agent_lifecycle_hooks import LifecycleHookResult, run_lifecycle_hooks
from vibeagent.agent_lifecycle_runtime import AgentLifecycleRuntime
from vibeagent.cli_interactive import run_interactive_loop
from vibeagent.file_changed_hooks import (
    FileChangedHookRuntime,
    FileChangedPollResult,
    static_watch_filenames,
)
from vibeagent.session_environment import ensure_session_environment_file
from vibeagent.session_file_watch_state import (
    read_dynamic_watch_paths,
    write_dynamic_watch_paths,
)
from vibeagent.session_working_directory import write_session_cwd
from vibeagent.types import (
    ApprovalDecision,
    AssistantResponse,
    ChatMessage,
    ContentBlock,
)
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hook_types import ProjectHook, ProjectHooks
from vibeagent.workspace_hooks import read_project_hooks
from vibeagent.workspace_permissions import ProjectPermissions


def _hook(matcher: str, command: str = "true") -> ProjectHook:
    return ProjectHook(
        event="FileChanged",
        matcher=matcher,
        command=command,
        timeout_ms=10_000,
        source="test",
    )


def _write_hooks(root: Path, payload: dict[str, object]) -> None:
    path = root / ".vibeagent" / "hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _approve(_request) -> ApprovalDecision:
    return ApprovalDecision(approved=True, message="approved")


class RecordingLifecycle:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int]] = []

    def file_changed(self, _workspace, path: str, event: str, *, iteration: int = 0):
        self.calls.append((path, event, iteration))
        return LifecycleHookResult(system_messages=(f"{event}:{Path(path).name}",))


class FileChangeClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


class FileChangedHookConfigTests(unittest.TestCase):
    def test_loads_file_changed_and_uses_empty_default_matcher(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-file-watch-") as base:
            root = Path(base)
            _write_hooks(
                root,
                {
                    "FileChanged": [
                        {"hooks": [{"type": "command", "command": "true"}]},
                        {
                            "matcher": ".envrc|.env",
                            "hooks": [{"type": "command", "command": "true"}],
                        },
                    ]
                },
            )

            config = read_project_hooks(create_run_workspace(root))

        self.assertIsNone(config.error)
        self.assertEqual([hook.matcher for hook in config.hooks], ["", ".envrc|.env"])
        self.assertEqual(static_watch_filenames(config), (".envrc", ".env"))
        self.assertFalse(config.requires_sequential_tools)

    def test_rejects_model_file_changed_handlers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-file-watch-") as base:
            root = Path(base)
            _write_hooks(
                root,
                {
                    "FileChanged": [
                        {
                            "matcher": ".env",
                            "hooks": [{"type": "prompt", "prompt": "inspect"}],
                        }
                    ]
                },
            )

            config = read_project_hooks(create_run_workspace(root))

        self.assertIn("do not support prompt handlers", config.error or "")


class FileWatchStateTests(unittest.TestCase):
    def test_dynamic_paths_are_atomic_bounded_and_workspace_scoped(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-file-watch-") as base:
            root = Path(base)
            workspace = create_run_workspace(root)
            target = root / "config" / "runtime.env"

            stored = write_dynamic_watch_paths(
                workspace,
                (str(target), str(target)),
            )

            self.assertEqual(stored, (target,))
            self.assertEqual(read_dynamic_watch_paths(workspace), (target,))
            with self.assertRaisesRegex(ValueError, "escapes"):
                write_dynamic_watch_paths(workspace, (str(root.parent / "outside.env"),))
            with self.assertRaisesRegex(ValueError, "protected"):
                write_dynamic_watch_paths(workspace, (str(root / ".git" / "config"),))

    def test_dynamic_paths_reject_symlink_components(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-file-watch-") as base:
            root = Path(base)
            outside = root.parent / f"{root.name}-outside"
            outside.mkdir()
            link = root / "linked"
            link.symlink_to(outside, target_is_directory=True)
            workspace = create_run_workspace(root)
            try:
                with self.assertRaisesRegex(ValueError, "symbolic link"):
                    write_dynamic_watch_paths(workspace, (str(link / "config.env"),))
            finally:
                link.unlink()
                outside.rmdir()


class FileWatchOutputTests(unittest.TestCase):
    def test_lifecycle_watch_paths_replace_dynamic_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-file-watch-") as base:
            root = Path(base)
            workspace = create_run_workspace(root)
            first = root / "first.env"
            hook = ProjectHook(
                event="SessionStart",
                matcher="startup",
                command="hook",
                timeout_ms=10_000,
                source="test",
            )
            output = HookRunResult(
                event="SessionStart",
                command="hook",
                source="test",
                status="passed",
                ok=True,
                exit_code=0,
                timed_out=False,
                stdout=json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "SessionStart",
                            "watchPaths": [str(first)],
                        }
                    }
                ),
                stderr="",
                message="passed",
            )
            with patch(
                "vibeagent.agent_lifecycle_hooks.run_project_hook",
                return_value=output,
            ):
                result = run_lifecycle_hooks(
                    workspace,
                    ProjectHooks(hooks=(hook,)),
                    "SessionStart",
                    "startup",
                    {"source": "startup"},
                    iteration=0,
                    command_timeout_ms=30_000,
                    logger=None,
                    approval_handler=None,
                    approval_policy="ask",
                    execute_action_safely_func=Mock(),
                    permissions=ProjectPermissions(),
                )

            self.assertEqual(result.watch_paths, (str(first),))
            self.assertEqual(read_dynamic_watch_paths(workspace), (first,))

            cleared = HookRunResult(
                event="FileChanged",
                command="hook",
                source="test",
                status="passed",
                ok=True,
                exit_code=0,
                timed_out=False,
                stdout=json.dumps({"watchPaths": []}),
                stderr="",
                message="passed",
            )
            file_hook = _hook("")
            with patch(
                "vibeagent.agent_lifecycle_hooks.run_project_hook",
                return_value=cleared,
            ):
                result = run_lifecycle_hooks(
                    workspace,
                    ProjectHooks(hooks=(file_hook,)),
                    "FileChanged",
                    "first.env",
                    {"file_path": str(first), "event": "change"},
                    iteration=1,
                    command_timeout_ms=30_000,
                    logger=None,
                    approval_handler=None,
                    approval_policy="ask",
                    execute_action_safely_func=Mock(),
                    permissions=ProjectPermissions(),
                )

            self.assertEqual(result.watch_paths, ())
            self.assertEqual(read_dynamic_watch_paths(workspace), ())


class FileChangedDetectorTests(unittest.TestCase):
    def test_detects_add_change_and_unlink_once(self) -> None:
        lifecycle = RecordingLifecycle()
        with tempfile.TemporaryDirectory(prefix="vibeagent-file-watch-") as base:
            root = Path(base)
            workspace = create_run_workspace(root)
            runtime = FileChangedHookRuntime(
                workspace,
                ProjectHooks(hooks=(_hook(".env"),)),
                lifecycle,  # type: ignore[arg-type]
            )
            target = root / ".env"

            self.assertEqual(runtime.poll().events, ())
            target.write_text("VALUE=1\n", encoding="utf-8")
            added = runtime.poll(iteration=2)
            self.assertEqual([(item.event, item.path) for item in added.events], [("add", target)])
            self.assertEqual(added.system_messages, ("add:.env",))
            self.assertEqual(runtime.poll().events, ())

            target.write_text("VALUE=22\n", encoding="utf-8")
            changed = runtime.poll(iteration=3)
            self.assertEqual([item.event for item in changed.events], ["change"])
            target.unlink()
            removed = runtime.poll(iteration=4)
            self.assertEqual([item.event for item in removed.events], ["unlink"])

        self.assertEqual(
            [(event, iteration) for _, event, iteration in lifecycle.calls],
            [("add", 2), ("change", 3), ("unlink", 4)],
        )

    def test_static_paths_follow_session_cwd_and_dynamic_paths_remain_absolute(self) -> None:
        lifecycle = RecordingLifecycle()
        with tempfile.TemporaryDirectory(prefix="vibeagent-file-watch-") as base:
            root = Path(base)
            nested = root / "nested"
            nested.mkdir()
            workspace = create_run_workspace(root)
            dynamic = root / "shared.env"
            write_dynamic_watch_paths(workspace, (str(dynamic),))
            runtime = FileChangedHookRuntime(
                workspace,
                ProjectHooks(hooks=(_hook("local.env"), _hook(""))),
                lifecycle,  # type: ignore[arg-type]
            )

            write_session_cwd(workspace, nested)
            runtime.poll()
            nested.joinpath("local.env").write_text("LOCAL=1\n", encoding="utf-8")
            dynamic.write_text("SHARED=1\n", encoding="utf-8")
            result = runtime.poll()

        self.assertEqual(
            {(item.event, item.path) for item in result.events},
            {("add", nested / "local.env"), ("add", dynamic)},
        )


class FileChangedHookRuntimeTests(unittest.TestCase):
    def test_real_hook_receives_input_updates_environment_and_cannot_block(self) -> None:
        command = (
            'python3 -c "import json,os,sys; d=json.load(sys.stdin); '
            "open(os.environ['CLAUDE_ENV_FILE'],'w').write('export WATCHED=1\\n'); "
            "print(json.dumps({'decision':'block','reason':'ignored','systemMessage':"
            "d['event'] + ':' + d['file_path']}))\""
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-file-watch-") as base:
            root = Path(base)
            _write_hooks(
                root,
                {
                    "FileChanged": [
                        {
                            "matcher": ".env",
                            "hooks": [{"type": "command", "command": command}],
                        }
                    ]
                },
            )
            workspace = create_run_workspace(root)
            hooks = read_project_hooks(workspace)
            lifecycle = AgentLifecycleRuntime(
                hooks=hooks,
                permissions=ProjectPermissions(),
                command_timeout_ms=30_000,
                logger=None,
                approval_handler=_approve,
                approval_policy="ask",
                execute_action_safely=execute_action_safely,
            )
            runtime = FileChangedHookRuntime(workspace, hooks, lifecycle)

            target = root / ".env"
            target.write_text("VALUE=1\n", encoding="utf-8")
            result = runtime.poll(iteration=2)
            environment = ensure_session_environment_file(workspace).read_text(encoding="utf-8")

        self.assertEqual(result.events[0].event, "add")
        self.assertEqual(result.system_messages, (f"add:{target}",))
        self.assertEqual(environment, "export WATCHED=1\n")

    def test_agent_polls_file_changes_before_next_model_turn(self) -> None:
        command = (
            'python3 -c "import json,sys; d=json.load(sys.stdin); '
            "print(json.dumps({'systemMessage':d['event'] + ':' + d['file_path']}))\""
        )
        client = FileChangeClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "write-1",
                        "name": "write_file",
                        "input": {"path": "watched.txt", "content": "ready\n"},
                    }
                ],
                [{"type": "text", "text": "done"}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-file-watch-") as base:
            root = Path(base)
            _write_hooks(
                root,
                {
                    "FileChanged": [
                        {
                            "matcher": "watched.txt",
                            "hooks": [{"type": "command", "command": command}],
                        }
                    ]
                },
            )

            result = run_agent(
                "write watched file",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=_approve,
            )

        expected = f"add:{root / 'watched.txt'}"
        self.assertTrue(result.success)
        self.assertEqual(result.hook_system_messages, [expected])
        self.assertEqual(len(client.messages), 2)
        self.assertNotIn(expected, str(client.messages))

    def test_interactive_idle_callback_polls_existing_session(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-file-watch-") as base:
            root = Path(base)
            create_run_workspace(root, run_id="watch-run")
            watcher = Mock()
            watcher.poll.return_value = FileChangedPollResult(
                system_messages=("watched file changed",)
            )
            updater = Mock()
            updater.collect_notifications.return_value = []
            stdout = io.StringIO()

            def idle_input(_prompt, callback, *, input_func):
                callback()
                return "/exit"

            old_cwd = Path.cwd()
            try:
                os.chdir(root)
                with (
                    patch("vibeagent.cli_interactive.prompt_project_permission_trust", return_value=False),
                    patch("vibeagent.cli_interactive.create_peer_runtime", return_value=None),
                    patch("vibeagent.cli_interactive.PluginAutoUpdateRuntime", return_value=updater),
                    patch(
                        "vibeagent.cli_interactive.create_interactive_file_changed_runtime",
                        return_value=watcher,
                    ) as create_watcher,
                    patch("vibeagent.cli_interactive.input_with_idle_callback", side_effect=idle_input),
                    redirect_stdout(stdout),
                ):
                    exit_code = run_interactive_loop(
                        command_namespace={},
                        initial_resume_run_id="watch-run",
                    )
            finally:
                os.chdir(old_cwd)

        self.assertEqual(exit_code, 0)
        create_watcher.assert_called_once()
        watcher.poll.assert_called_once_with(iteration=0)
        self.assertIn("watched file changed", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
