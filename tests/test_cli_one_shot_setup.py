from __future__ import annotations

from pathlib import Path
import unittest

from vibeagent.cli_one_shot_setup import resolve_one_shot_project_setup, resolve_one_shot_runtime_setup
from vibeagent.config import ExecutionConfig


class CliOneShotSetupTests(unittest.TestCase):
    def test_project_setup_resolves_task_metadata_and_mcp_paths(self) -> None:
        root = Path("/project")
        calls: list[tuple[str, object]] = []
        metadata = {"source": "project_command", "name": "fix"}
        mcp_paths = (root / ".mcp.json",)

        def resolve_code_task(*args, **kwargs):
            calls.append(("task_args", args))
            calls.append(("task_kwargs", kwargs))
            return "expanded task", metadata

        def resolve_mcp(project_root, values):
            calls.append(("mcp", (project_root, values)))
            return mcp_paths

        setup = resolve_one_shot_project_setup(
            "/fix bug",
            request_mode="code",
            project_root=root,
            mcp_config_paths=[".mcp.json"],
            resolve_code_task_func=resolve_code_task,
            resolve_mcp_config_paths_func=resolve_mcp,
        )

        self.assertEqual(setup.task, "expanded task")
        self.assertIs(setup.task_metadata, metadata)
        self.assertEqual(setup.mcp_config_paths, mcp_paths)
        self.assertEqual(calls[0], ("task_args", ("/fix bug",)))
        self.assertEqual(calls[1], ("task_kwargs", {"request_mode": "code", "project_root": root}))
        self.assertEqual(calls[2], ("mcp", (root, [".mcp.json"])))

    def test_project_setup_preserves_task_resolution_errors(self) -> None:
        def resolve_code_task(*args, **kwargs):
            raise ValueError("Unknown project command: /missing")

        with self.assertRaisesRegex(ValueError, "Unknown project command"):
            resolve_one_shot_project_setup(
                "/missing",
                request_mode="code",
                project_root=Path("/project"),
                mcp_config_paths=None,
                resolve_code_task_func=resolve_code_task,
                resolve_mcp_config_paths_func=lambda root, values: (),
            )

    def test_project_setup_preserves_mcp_resolution_errors(self) -> None:
        calls: list[str] = []

        def resolve_mcp(project_root, values):
            calls.append("mcp")
            raise ValueError("--mcp-config file not found: missing.json.")

        with self.assertRaisesRegex(ValueError, "--mcp-config file not found"):
            resolve_one_shot_project_setup(
                "fix tests",
                request_mode="code",
                project_root=Path("/project"),
                mcp_config_paths=["missing.json"],
                resolve_code_task_func=lambda *args, **kwargs: ("fix tests", None),
                resolve_mcp_config_paths_func=resolve_mcp,
            )

        self.assertEqual(calls, ["mcp"])

    def test_runtime_setup_resolves_execution_config_and_provider_env(self) -> None:
        root = Path("/project")
        execution = ExecutionConfig(max_iterations=7, command_timeout_ms=123)
        provider_env = {"VIBEAGENT_PROVIDER": "minimax"}
        calls: list[tuple[str, object]] = []
        provider_args = object()

        def resolve_execution(config_root, **kwargs):
            calls.append(("execution", (config_root, kwargs)))
            return execution

        def build_env(args, config_root):
            calls.append(("provider", (args, config_root)))
            return provider_env

        setup = resolve_one_shot_runtime_setup(
            config_root=root,
            provider_args=provider_args,
            max_iterations=7,
            command_timeout_ms=123,
            max_output_tokens=2048,
            model_retries=2,
            model_retry_delay_ms=50,
            model_timeout_ms=30000,
            resolve_execution_config_func=resolve_execution,
            build_provider_env_func=build_env,
        )

        self.assertIs(setup.execution_config, execution)
        self.assertIs(setup.provider_env, provider_env)
        self.assertEqual(
            calls[0],
            (
                "execution",
                (
                    root,
                    {
                        "max_iterations": 7,
                        "command_timeout_ms": 123,
                        "max_output_tokens": 2048,
                        "model_retries": 2,
                        "model_retry_delay_ms": 50,
                        "model_timeout_ms": 30000,
                    },
                ),
            ),
        )
        self.assertEqual(calls[1], ("provider", (provider_args, root)))


if __name__ == "__main__":
    unittest.main()
