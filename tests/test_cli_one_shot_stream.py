from __future__ import annotations

from contextlib import contextmanager, nullcontext
from pathlib import Path
from types import SimpleNamespace
import unittest

from vibeagent.cli_one_shot_stream import build_one_shot_stream_scope
from vibeagent.cli_stream_output import JsonEventStream


class CliOneShotStreamTests(unittest.TestCase):
    def test_stream_scope_skips_workspace_without_stream(self) -> None:
        calls: list[str] = []

        scope = build_one_shot_stream_scope(
            None,
            project_root=Path("/project"),
            mcp_config_paths=(),
            strict_mcp_config=False,
            create_workspace_func=lambda *args, **kwargs: calls.append("workspace"),
            observe_events_func=lambda *args, **kwargs: calls.append("events"),
        )

        self.assertIsNone(scope.workspace)
        self.assertEqual(calls, [])
        with scope.event_scope:
            pass

    def test_force_workspace_creates_branch_target_without_stream_observer(self) -> None:
        workspace = SimpleNamespace(session_dir=Path("/project/.vibeagent/sessions/run-1"))
        calls: list[str] = []

        scope = build_one_shot_stream_scope(
            None,
            project_root=Path("/project"),
            mcp_config_paths=(),
            strict_mcp_config=False,
            force_workspace=True,
            create_workspace_func=lambda *args, **kwargs: calls.append("workspace") or workspace,
            observe_events_func=lambda *args, **kwargs: calls.append("events") or nullcontext(),
        )

        self.assertIs(scope.workspace, workspace)
        self.assertEqual(calls, ["workspace"])
        with scope.event_scope:
            pass

    def test_stream_scope_creates_workspace_and_event_observer(self) -> None:
        stream = JsonEventStream()
        project_root = Path("/project")
        mcp_config = (Path("/project/.mcp.json"),)
        workspace = SimpleNamespace(session_dir=Path("/project/.vibeagent/runs/run-1"))
        calls: list[tuple[str, object]] = []

        def create_workspace(*args, **kwargs):
            calls.append(("workspace_args", args))
            calls.append(("workspace_kwargs", kwargs))
            return workspace

        @contextmanager
        def event_scope():
            calls.append(("events_entered", True))
            yield
            calls.append(("events_exited", True))

        def observe_events(*args, **kwargs):
            calls.append(("events_args", args))
            calls.append(("events_kwargs", kwargs))
            return event_scope()

        scope = build_one_shot_stream_scope(
            stream,
            project_root=project_root,
            mcp_config_paths=mcp_config,
            strict_mcp_config=True,
            create_workspace_func=create_workspace,
            observe_events_func=observe_events,
        )

        self.assertIs(scope.workspace, workspace)
        self.assertEqual(calls[0], ("workspace_args", (project_root,)))
        self.assertEqual(
            calls[1],
            ("workspace_kwargs", {"mcp_config_paths": mcp_config, "strict_mcp_config": True}),
        )
        self.assertEqual(calls[2], ("events_args", (workspace.session_dir, stream.session_event)))
        self.assertEqual(calls[3], ("events_kwargs", {}))
        with scope.event_scope:
            pass
        self.assertEqual(calls[-2:], [("events_entered", True), ("events_exited", True)])

    def test_stream_scope_passes_additional_roots_to_workspace(self) -> None:
        stream = JsonEventStream()
        shared = Path("/shared").resolve()
        calls: list[dict[str, object]] = []
        workspace = SimpleNamespace(session_dir=Path("/project/.vibeagent/runs/run-1"))

        scope = build_one_shot_stream_scope(
            stream,
            project_root=Path("/project"),
            mcp_config_paths=(),
            strict_mcp_config=False,
            additional_roots=(shared,),
            create_workspace_func=lambda *args, **kwargs: calls.append(kwargs) or workspace,
            observe_events_func=lambda *args, **kwargs: nullcontext(),
        )

        self.assertIs(scope.workspace, workspace)
        self.assertEqual(calls[0]["additional_roots"], (shared,))

    def test_stream_scope_observes_passed_resume_workspace_without_replacing_it(self) -> None:
        stream = JsonEventStream()
        workspace = SimpleNamespace(session_dir=Path("/project/.vibeagent/sessions/run-old"))
        calls: list[tuple[object, ...]] = []

        scope = build_one_shot_stream_scope(
            stream,
            project_root=Path("/project"),
            mcp_config_paths=(),
            strict_mcp_config=False,
            workspace=workspace,
            create_workspace_func=lambda *args, **kwargs: self.fail("resume workspace must be reused"),
            observe_events_func=lambda *args, **kwargs: calls.append(args) or nullcontext(),
        )

        self.assertIs(scope.workspace, workspace)
        self.assertEqual(calls, [(workspace.session_dir, stream.session_event)])


if __name__ == "__main__":
    unittest.main()
