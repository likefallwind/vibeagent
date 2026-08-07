import unittest

from vibeagent import config
from vibeagent import config_execution


class ConfigExecutionTests(unittest.TestCase):
    def test_config_reexports_execution_helpers(self) -> None:
        names = [
            "DEFAULT_MAX_ITERATIONS",
            "DEFAULT_COMMAND_TIMEOUT_MS",
            "DEFAULT_MAX_OUTPUT_TOKENS",
            "DEFAULT_MODEL_RETRIES",
            "DEFAULT_MODEL_RETRY_DELAY_MS",
            "DEFAULT_MODEL_TIMEOUT_MS",
            "ExecutionConfig",
            "read_optional_positive_int",
            "read_optional_nonnegative_int",
            "read_optional_timeout_ms",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(config, name), getattr(config_execution, name))

    def test_execution_resolver_uses_supplied_config_reader(self) -> None:
        execution = config_execution.resolve_execution_config(
            "/tmp/project",
            max_iterations=3,
            read_project_config_func=lambda root: {
                "max_iterations": 9,
                "command_timeout_ms": "45000",
                "max_output_tokens": "8192",
                "model_retries": 0,
                "model_retry_delay_ms": 0,
                "model_timeout_ms": 45000,
            },
        )

        self.assertEqual(execution.max_iterations, 3)
        self.assertEqual(execution.command_timeout_ms, 45000)
        self.assertEqual(execution.max_output_tokens, 8192)
        self.assertEqual(execution.model_retries, 0)
        self.assertEqual(execution.model_retry_delay_ms, 0)
        self.assertEqual(execution.model_timeout_ms, 45000)


if __name__ == "__main__":
    unittest.main()
