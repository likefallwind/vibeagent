from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.agent_execution_support import execute_action_safely
from vibeagent.agent_lifecycle_hooks import LifecycleHookResult
from vibeagent.agent_lifecycle_runtime import AgentLifecycleRuntime
from vibeagent.config_change_hooks import ConfigChangeHookRuntime
from vibeagent.session_config_state import (
    effective_settings_path,
    initialize_config_state,
    read_config_state,
    write_config_state,
)
from vibeagent.plugin_scope_settings import effective_plugin_enabled
from vibeagent.types import ApprovalDecision, ApprovalRequest
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_hooks import read_project_hooks
from vibeagent.workspace_permissions import ProjectPermissions
from vibeagent.workspace_skills import read_project_skill


def _approve(_request: ApprovalRequest) -> ApprovalDecision:
    return ApprovalDecision(approved=True, message="test")


class RecordingLifecycle:
    def __init__(self, *, blocked: bool) -> None:
        self.blocked = blocked
        self.calls: list[tuple[str, str | None, int]] = []

    def config_change(
        self,
        _workspace,
        source: str,
        *,
        file_path: str | None = None,
        iteration: int = 0,
    ) -> LifecycleHookResult:
        self.calls.append((source, file_path, iteration))
        return LifecycleHookResult(
            system_messages=(f"checked:{source}",),
            blocking_message="keep old config" if self.blocked else None,
        )


class ConfigChangeRuntimeTests(unittest.TestCase):
    def test_old_config_state_captures_nested_skills_without_change_event(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-config-change-") as base:
            root = Path(base)
            home = root / "home"
            home.mkdir()
            skill = root / "apps/web/.claude/skills/demo/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(self._skill("nested instructions"), encoding="utf-8")
            workspace = create_run_workspace(root, run_id="old-config-run")
            lifecycle = RecordingLifecycle(blocked=False)
            with self._home(home):
                state = initialize_config_state(workspace)
                state.pop("nested_project_skills")
                write_config_state(workspace, state)
                ConfigChangeHookRuntime(workspace, lifecycle)  # type: ignore[arg-type]
                loaded = read_project_skill(workspace, "apps/web:demo")
                migrated = read_config_state(workspace)

            self.assertIn("nested instructions", loaded["content"])
            self.assertIn("nested_project_skills", migrated or {})
            self.assertEqual(lifecycle.calls, [])

    def test_blocked_settings_change_keeps_session_snapshot(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-config-change-") as base:
            root = Path(base)
            home = root / "home"
            home.mkdir()
            settings = root / ".claude/settings.json"
            settings.parent.mkdir()
            settings.write_text('{"agent":"old"}\n', encoding="utf-8")
            workspace = create_run_workspace(root, run_id="config-run")
            lifecycle = RecordingLifecycle(blocked=True)
            with self._home(home):
                runtime = ConfigChangeHookRuntime(workspace, lifecycle)  # type: ignore[arg-type]
                snapshot = effective_settings_path(workspace, settings)
                settings.write_text('{"agent":"new"}\n', encoding="utf-8")
                result = runtime.poll(iteration=3)
                repeated = runtime.poll(iteration=4)

            self.assertEqual(snapshot.read_text(encoding="utf-8"), '{"agent":"old"}\n')
            self.assertTrue(result.events[0].blocked)
            self.assertEqual(result.events[0].source, "project_settings")
            self.assertIn("keep old config", result.system_messages[-1])
            self.assertEqual(repeated.events, ())
            self.assertEqual(lifecycle.calls[0], ("project_settings", str(settings), 3))

    def test_blocked_enabled_plugin_change_uses_session_snapshot(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-config-change-") as base:
            root = Path(base)
            home = root / "home"
            home.mkdir()
            settings = root / ".claude/settings.json"
            settings.parent.mkdir()
            settings.write_text(
                '{"enabledPlugins":{"demo":true}}\n', encoding="utf-8"
            )
            workspace = create_run_workspace(root, run_id="config-run")
            with self._home(home):
                runtime = ConfigChangeHookRuntime(  # type: ignore[arg-type]
                    workspace, RecordingLifecycle(blocked=True)
                )
                settings.write_text(
                    '{"enabledPlugins":{"demo":false}}\n', encoding="utf-8"
                )
                runtime.poll()
                enabled = effective_plugin_enabled(
                    root, "demo", fallback=False, workspace=workspace
                )

            self.assertTrue(enabled)

    def test_allowed_settings_change_updates_session_snapshot(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-config-change-") as base:
            root = Path(base)
            home = root / "home"
            home.mkdir()
            settings = root / ".claude/settings.local.json"
            settings.parent.mkdir()
            settings.write_text('{"agent":"old"}\n', encoding="utf-8")
            workspace = create_run_workspace(root, run_id="config-run")
            with self._home(home):
                runtime = ConfigChangeHookRuntime(  # type: ignore[arg-type]
                    workspace, RecordingLifecycle(blocked=False)
                )
                settings.write_text('{"agent":"new"}\n', encoding="utf-8")
                result = runtime.poll()
                snapshot = effective_settings_path(workspace, settings)

            self.assertFalse(result.events[0].blocked)
            self.assertEqual(snapshot.read_text(encoding="utf-8"), '{"agent":"new"}\n')

    def test_blocked_skill_change_keeps_old_skill_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-config-change-") as base:
            root = Path(base)
            home = root / "home"
            home.mkdir()
            skill = root / ".claude/skills/demo/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(self._skill("old instructions"), encoding="utf-8")
            workspace = create_run_workspace(root, run_id="config-run")
            lifecycle = RecordingLifecycle(blocked=True)
            with self._home(home):
                runtime = ConfigChangeHookRuntime(workspace, lifecycle)  # type: ignore[arg-type]
                skill.write_text(self._skill("new instructions"), encoding="utf-8")
                result = runtime.poll()
                loaded = read_project_skill(workspace, "demo")

            self.assertEqual(result.events[0].source, "skills")
            self.assertTrue(result.events[0].blocked)
            self.assertIn("old instructions", loaded["content"])
            self.assertNotIn("new instructions", loaded["content"])

    def test_blocked_nested_skill_change_keeps_old_skill_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-config-change-") as base:
            root = Path(base)
            home = root / "home"
            home.mkdir()
            skill = root / "apps/web/.claude/skills/demo/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(self._skill("old nested instructions"), encoding="utf-8")
            workspace = create_run_workspace(root, run_id="nested-config-run")
            lifecycle = RecordingLifecycle(blocked=True)
            with self._home(home):
                runtime = ConfigChangeHookRuntime(workspace, lifecycle)  # type: ignore[arg-type]
                skill.write_text(self._skill("new nested instructions"), encoding="utf-8")
                result = runtime.poll()
                loaded = read_project_skill(workspace, "apps/web:demo")

            self.assertEqual(len(result.events), 1)
            self.assertEqual(result.events[0].source, "skills")
            self.assertTrue(result.events[0].blocked)
            self.assertIn("old nested instructions", loaded["content"])
            self.assertNotIn("new nested instructions", loaded["content"])

    def test_real_hook_receives_source_and_blocks_change(self) -> None:
        script = """import json, pathlib, sys
payload = json.load(sys.stdin)
pathlib.Path('config-input.json').write_text(json.dumps(payload), encoding='utf-8')
print(json.dumps({'decision': 'block', 'reason': 'review required'}))
"""
        with tempfile.TemporaryDirectory(prefix="vibeagent-config-change-") as base:
            root = Path(base)
            home = root / "home"
            home.mkdir()
            (root / "hook.py").write_text(script, encoding="utf-8")
            settings = root / ".claude/settings.json"
            settings.parent.mkdir()
            settings.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "ConfigChange": [
                                {
                                    "matcher": "project_settings",
                                    "hooks": [
                                        {"type": "command", "command": "python3 hook.py"}
                                    ],
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            workspace = create_run_workspace(root, run_id="config-run")
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
            with self._home(home):
                runtime = ConfigChangeHookRuntime(workspace, lifecycle)
                settings.write_text("{}\n", encoding="utf-8")
                result = runtime.poll(iteration=2)
            payload = json.loads((root / "config-input.json").read_text(encoding="utf-8"))

            self.assertTrue(result.events[0].blocked)
            self.assertEqual(result.events[0].reason, "review required")
            self.assertEqual(payload["hook_event_name"], "ConfigChange")
            self.assertEqual(payload["source"], "project_settings")
            self.assertEqual(payload["file_path"], str(settings))

    @staticmethod
    def _skill(body: str) -> str:
        return f"---\nname: demo\ndescription: Demo skill\n---\n{body}\n"

    @staticmethod
    def _home(home: Path):
        return _MultiPatch(
            patch("vibeagent.session_config_state.user_home", return_value=home),
            patch("vibeagent.workspace_settings_sources.user_home", return_value=home),
            patch("vibeagent.workspace_skills.user_home", return_value=home),
        )


class _MultiPatch:
    def __init__(self, *patchers) -> None:
        self.patchers = patchers

    def __enter__(self):
        for patcher in self.patchers:
            patcher.start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        for patcher in reversed(self.patchers):
            patcher.stop()


if __name__ == "__main__":
    unittest.main()
