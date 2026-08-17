import argparse
import unittest
from pathlib import Path

from vibeagent import cli as cli_module
from vibeagent import cli_command_namespace, commands as commands_module
from vibeagent.cli_local_dispatch import LOCAL_FLAG_HANDLER_NAMES, dispatch_local_flag
from vibeagent.command_namespace_exports import command_export_names


class CliCommandDispatchTests(unittest.TestCase):
    def test_cli_reexports_command_namespace_helpers(self) -> None:
        missing_or_changed = [
            name
            for name in cli_command_namespace.__all__
            if getattr(cli_module, name, None) is not getattr(commands_module, name, None)
        ]

        self.assertEqual([], missing_or_changed)
        self.assertIn("get_read_text", cli_command_namespace.__all__)
        self.assertIn("format_review_report_text", cli_command_namespace.__all__)
        self.assertIn("parse_local_command", cli_command_namespace.__all__)

    def test_cli_command_namespace_uses_public_command_exports_only(self) -> None:
        self.assertEqual(len(commands_module.__all__), 577)
        self.assertEqual(command_export_names(commands_module), commands_module.__all__)
        self.assertEqual(command_export_names(commands_module), cli_command_namespace.__all__)
        self.assertIn("get_agents_text", cli_command_namespace.__all__)
        self.assertIn("get_skills_text", cli_command_namespace.__all__)
        self.assertIn("get_hooks_report", cli_command_namespace.__all__)
        self.assertIn("get_hooks_text", cli_command_namespace.__all__)
        self.assertIn("format_hooks_report_text", cli_command_namespace.__all__)
        self.assertNotIn("format_tool_property", cli_command_namespace.__all__)
        self.assertNotIn("get_blocked_command_reason", cli_command_namespace.__all__)

    def test_dispatch_local_flag_preserves_order_and_handler_signatures(self) -> None:
        args = argparse.Namespace()
        project_root = Path("/tmp/project")
        config_root = Path("/tmp/config")
        provider_env = {"VIBEAGENT_PROVIDER": "minimax"}
        calls: list[tuple[str, object, ...]] = []

        def generic_handler(name: str, result: tuple[str, dict[str, object]] | None = None):
            def run(args, project_root, commands):
                calls.append((name, project_root, commands))
                return result

            return run

        def project_handler(name: str, result: tuple[str, dict[str, object]] | None = None):
            def run(args, project_root, config_root, provider_env, commands):
                calls.append((name, project_root, config_root, provider_env, commands))
                return result

            return run

        def review_handler(result: tuple[str, dict[str, object]] | None = None):
            def run(args, project_root, provider_env, commands):
                calls.append(("run_review_local_flag", project_root, provider_env, commands))
                return result

            return run

        namespace = {
            name: (
                review_handler(("review text", {"review": {"ok": True}}))
                if name == "run_review_local_flag"
                else project_handler(name)
                if name == "run_project_local_flag"
                else generic_handler(name)
            )
            for name in LOCAL_FLAG_HANDLER_NAMES
        }

        result = dispatch_local_flag(args, project_root, config_root, provider_env, namespace)

        self.assertEqual(result, ("review text", {"review": {"ok": True}}))
        review_index = LOCAL_FLAG_HANDLER_NAMES.index("run_review_local_flag")
        self.assertEqual([call[0] for call in calls], list(LOCAL_FLAG_HANDLER_NAMES[: review_index + 1]))
        self.assertEqual(calls[0], ("run_background_agent_local_flag", project_root, namespace))
        self.assertEqual(calls[1], ("run_mcp_local_flag", project_root, namespace))
        self.assertEqual(calls[2], ("run_project_local_flag", project_root, config_root, provider_env, namespace))
        self.assertEqual(calls[3], ("run_command_local_flag", project_root, namespace))
        self.assertEqual(calls[-1], ("run_review_local_flag", project_root, provider_env, namespace))


if __name__ == "__main__":
    unittest.main()
