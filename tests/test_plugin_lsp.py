from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from vibeagent.actions import execute_action, parse_tool_action
from vibeagent.agent import run_agent
from vibeagent.lsp_config import read_lsp_server_configs
from vibeagent.lsp_runtime import close_project_lsp
from vibeagent.plugin_manifest import read_plugin_manifest
from vibeagent.plugin_store import install_local_plugin, set_plugin_enabled
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace_core import create_run_workspace

try:
    from .lsp_test_support import write_lsp_plugin
except ImportError:  # unittest discover -s tests imports test modules as top-level names.
    from lsp_test_support import write_lsp_plugin


class ScriptedClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


class PluginLspTests(unittest.TestCase):
    def test_file_config_is_inventoried_expanded_and_namespaced(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-lsp-") as base:
            root = Path(base)
            plugin = write_lsp_plugin(root)
            manifest = read_plugin_manifest(plugin)
            self.assertEqual(manifest.component_count, 1)
            self.assertEqual([path.name for path in manifest.lsp_files], [".lsp.json"])

            install_local_plugin(root, "extensions/python-lsp")
            workspace = create_run_workspace(root, "run-1")
            configs = read_lsp_server_configs(workspace)

            self.assertEqual([config.name for config in configs], ["python-lsp.python"])
            self.assertEqual(configs[0].extension_to_language, {".py": "python"})
            self.assertIn(".vibeagent/plugins/cache/python-lsp/bin/server.py", configs[0].args[0])

    def test_inline_config_and_unsupported_socket_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-lsp-") as base:
            root = Path(base)
            plugin = write_lsp_plugin(root, inline=True)
            manifest = read_plugin_manifest(plugin)
            self.assertIsNotNone(manifest.inline_lsp_servers)
            install_local_plugin(root, "extensions/python-lsp")
            self.assertEqual(len(read_lsp_server_configs(create_run_workspace(root, "run-1"))), 1)

        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-lsp-") as base:
            root = Path(base)
            write_lsp_plugin(root, transport="socket")
            install_local_plugin(root, "extensions/python-lsp")
            with self.assertRaisesRegex(ValueError, "transport must be 'stdio'"):
                read_lsp_server_configs(create_run_workspace(root, "run-1"))

    def test_real_stdio_server_handles_navigation_and_disabled_fallback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-lsp-") as base:
            root = Path(base)
            write_lsp_plugin(root)
            install_local_plugin(root, "extensions/python-lsp")
            (root / "app.py").write_text("def greet(name):\n    return name\n", encoding="utf-8")
            workspace = create_run_workspace(root, "run-1")
            try:
                observation = execute_action(
                    workspace,
                    parse_tool_action(
                        "LSP",
                        {"operation": "goToDefinition", "filePath": "app.py", "line": 1, "character": 5},
                    ),
                )
                self.assertEqual(observation.kind, "lsp_query")
                self.assertEqual(observation.server, "python-lsp.python")
                self.assertEqual(observation.results[0]["path"], "app.py")

                set_plugin_enabled(root, "python-lsp", False)
                close_project_lsp(root)
                fallback = execute_action(
                    workspace,
                    parse_tool_action(
                        "LSP",
                        {"operation": "goToDefinition", "filePath": "app.py", "line": 1, "character": 5},
                    ),
                )
                self.assertEqual(fallback.kind, "python_definitions")
            finally:
                close_project_lsp(root)

    def test_conflicting_extensions_and_start_failures_are_bounded(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-lsp-") as base:
            root = Path(base)
            plugin = write_lsp_plugin(root)
            config_path = plugin / ".lsp.json"
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["second"] = dict(payload["python"])
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            install_local_plugin(root, "extensions/python-lsp")
            (root / "app.py").write_text("value = 1\n", encoding="utf-8")
            observation = execute_action(
                create_run_workspace(root, "run-1"),
                parse_tool_action(
                    "LSP",
                    {"operation": "hover", "filePath": "app.py", "line": 1, "character": 1},
                ),
            )
            self.assertEqual(observation.kind, "tool_error")
            self.assertIn("Multiple enabled LSP servers claim .py", observation.message)

        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-lsp-") as base:
            root = Path(base)
            plugin = write_lsp_plugin(root)
            config_path = plugin / ".lsp.json"
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["python"]["command"] = "vibeagent-command-that-does-not-exist"
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            install_local_plugin(root, "extensions/python-lsp")
            (root / "app.py").write_text("value = 1\n", encoding="utf-8")
            observation = execute_action(
                create_run_workspace(root, "run-1"),
                parse_tool_action(
                    "LSP",
                    {"operation": "hover", "filePath": "app.py", "line": 1, "character": 1},
                ),
            )
            self.assertEqual(observation.kind, "tool_error")
            self.assertIn("Could not start LSP server", observation.message)

    def test_malformed_server_protocol_becomes_tool_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-lsp-") as base:
            root = Path(base)
            plugin = write_lsp_plugin(root)
            (plugin / "bin" / "server.py").write_text(
                "import sys\nsys.stdout.buffer.write(b'Invalid\\r\\n\\r\\n')\nsys.stdout.buffer.flush()\n",
                encoding="utf-8",
            )
            install_local_plugin(root, "extensions/python-lsp")
            (root / "app.py").write_text("value = 1\n", encoding="utf-8")
            try:
                observation = execute_action(
                    create_run_workspace(root, "run-1"),
                    parse_tool_action(
                        "LSP",
                        {"operation": "hover", "filePath": "app.py", "line": 1, "character": 1},
                    ),
                )
            finally:
                close_project_lsp(root)
            self.assertEqual(observation.kind, "tool_error")
            self.assertIn("LSP server python-lsp.python failed", observation.message)

    def test_crashed_server_restarts_within_declared_policy(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-lsp-") as base:
            root = Path(base)
            plugin = write_lsp_plugin(root)
            config_path = plugin / ".lsp.json"
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["python"].update(
                {
                    "env": {"FAKE_LSP_CRASH_ONCE": "${CLAUDE_PROJECT_DIR}/crash.marker"},
                    "restartOnCrash": True,
                    "maxRestarts": 1,
                }
            )
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            install_local_plugin(root, "extensions/python-lsp")
            (root / "app.py").write_text("value = 1\n", encoding="utf-8")
            workspace = create_run_workspace(root, "run-1")
            action = parse_tool_action(
                "LSP",
                {"operation": "hover", "filePath": "app.py", "line": 1, "character": 1},
            )
            try:
                first = execute_action(workspace, action)
                second = execute_action(workspace, action)
            finally:
                close_project_lsp(root)
            self.assertEqual(first.kind, "tool_error")
            self.assertEqual(second.kind, "lsp_query")

    def test_successful_edit_returns_automatic_diagnostics_to_model(self) -> None:
        client = ScriptedClient(
            [
                [{"type": "tool_call", "id": "write-1", "name": "write_file", "input": {"path": "app.py", "content": "BROKEN\n"}}],
                [{"type": "text", "text": "done"}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-lsp-") as base:
            root = Path(base)
            write_lsp_plugin(root)
            install_local_plugin(root, "extensions/python-lsp")
            try:
                result = run_agent(
                    "Write the file",
                    base_dir=root,
                    client=client,
                    max_iterations=2,
                    approval_handler=lambda _request: ApprovalDecision(approved=True, message="approved"),
                )
                payload = json.loads(client.messages[1][-1].content[0]["content"])
            finally:
                close_project_lsp(root)

        self.assertTrue(result.success)
        self.assertEqual(
            [item.kind for item in result.observations[:2]],
            ["write_file", "lsp_diagnostics"],
        )
        diagnostics = payload["additionalResults"][0]
        self.assertTrue(diagnostics["ok"])
        self.assertEqual(diagnostics["diagnostics"][0]["message"], "BROKEN token")


if __name__ == "__main__":
    unittest.main()
