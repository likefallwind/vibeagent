from decimal import Decimal
import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.config import (
    load_project_config_env,
    normalize_api_key,
    resolve_cost_rates,
    resolve_execution_config,
    resolve_provider_config,
    save_project_config,
)
from vibeagent.providers import get_model_text


class ConfigTests(unittest.TestCase):
    def test_resolve_provider_config_defaults_to_minimax(self) -> None:
        config = resolve_provider_config({"MINIMAX_API_KEY": "key"})

        self.assertEqual(config.provider, "minimax")
        self.assertEqual(config.model, "MiniMax-M2.7")
        self.assertEqual(config.base_url, "https://api.minimaxi.com/anthropic")
        self.assertEqual(config.api_key, "key")
        self.assertEqual(config.api_key_source, "MINIMAX_API_KEY")

    def test_minimax_key_priority_and_bearer_normalization(self) -> None:
        config = resolve_provider_config(
            {
                "VIBEAGENT_PROVIDER": "minimax",
                "MINIMAX_API_KEY": " Bearer primary ",
                "MINIMAX_API": "alias",
                "minimax_api": "fallback",
            }
        )

        self.assertEqual(config.api_key, "primary")
        self.assertEqual(config.api_key_source, "MINIMAX_API_KEY")
        self.assertEqual(normalize_api_key(" Bearer copied-key "), "copied-key")

    def test_openai_compatible_defaults_and_key_priority(self) -> None:
        config = resolve_provider_config(
            {
                "VIBEAGENT_PROVIDER": "deepseek",
                "OPENAI_COMPAT_API_KEY": "openai-key",
                "DEEPSEEK_API_KEY": "deepseek-key",
            }
        )

        self.assertEqual(config.provider, "deepseek")
        self.assertEqual(config.model, "deepseek-chat")
        self.assertEqual(config.base_url, "https://api.deepseek.com")
        self.assertEqual(config.api_key, "openai-key")
        self.assertEqual(config.api_key_source, "OPENAI_COMPAT_API_KEY")

    def test_openai_compatible_deepseek_fallbacks(self) -> None:
        config = resolve_provider_config(
            {
                "VIBEAGENT_PROVIDER": "openai-compatible",
                "DEEPSEEK_API_KEY": "deepseek-key",
                "DEEPSEEK_MODEL": "deepseek-reasoner",
                "DEEPSEEK_BASE_URL": "https://deepseek.example/",
            }
        )

        self.assertEqual(config.model, "deepseek-reasoner")
        self.assertEqual(config.base_url, "https://deepseek.example")
        self.assertEqual(config.api_key_source, "DEEPSEEK_API_KEY")

    def test_generic_model_and_base_url_config_apply_to_selected_provider(self) -> None:
        config = resolve_provider_config(
            {
                "VIBEAGENT_PROVIDER": "deepseek",
                "VIBEAGENT_MODEL": "generic-model",
                "VIBEAGENT_BASE_URL": "https://generic.example/",
                "OPENAI_COMPAT_API_KEY": "key",
            }
        )

        self.assertEqual(config.model, "generic-model")
        self.assertEqual(config.base_url, "https://generic.example")

    def test_load_project_config_env_reads_non_secret_project_defaults(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-config-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps(
                    {
                        "provider": "deepseek",
                        "model": "deepseek-reasoner",
                        "base_url": "https://deepseek.example",
                        "api_key": "SHOULD_NOT_LOAD",
                        "input_usd_per_million": "0.1",
                    }
                ),
                encoding="utf-8",
            )

            env = load_project_config_env(base)

        self.assertEqual(env["VIBEAGENT_PROVIDER"], "deepseek")
        self.assertEqual(env["VIBEAGENT_MODEL"], "deepseek-reasoner")
        self.assertEqual(env["VIBEAGENT_BASE_URL"], "https://deepseek.example")
        self.assertEqual(env["VIBEAGENT_INPUT_USD_PER_MILLION"], "0.1")
        self.assertNotIn("api_key", env)
        self.assertNotIn("OPENAI_COMPAT_API_KEY", env)

    def test_load_project_config_env_rejects_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-config-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text("{bad", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Invalid .vibeagent/config.json"):
                load_project_config_env(base)

    def test_resolve_execution_config_reads_project_defaults(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-config-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps({"max_iterations": "12", "command_timeout_ms": 45000}),
                encoding="utf-8",
            )

            config = resolve_execution_config(base)

        self.assertEqual(config.max_iterations, 12)
        self.assertEqual(config.command_timeout_ms, 45000)

    def test_resolve_execution_config_cli_values_override_project_defaults(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-config-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps({"max_iterations": 12, "command_timeout_ms": 45000}),
                encoding="utf-8",
            )

            config = resolve_execution_config(base, max_iterations=3, command_timeout_ms=1000)

        self.assertEqual(config.max_iterations, 3)
        self.assertEqual(config.command_timeout_ms, 1000)

    def test_resolve_execution_config_rejects_invalid_project_defaults(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-config-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps({"max_iterations": 0, "command_timeout_ms": 99}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "max_iterations must be a positive integer"):
                resolve_execution_config(base)

    def test_save_project_config_writes_non_secret_defaults(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-config-") as base:
            text = save_project_config(
                base,
                provider="deepseek",
                model="deepseek-reasoner",
                base_url="https://deepseek.example",
                max_iterations=15,
                command_timeout_ms=60000,
            )
            data = json.loads((Path(base) / ".vibeagent" / "config.json").read_text(encoding="utf-8"))

        self.assertEqual(text, "Saved .vibeagent/config.json.")
        self.assertEqual(
            data,
            {
                "base_url": "https://deepseek.example",
                "command_timeout_ms": 60000,
                "max_iterations": 15,
                "model": "deepseek-reasoner",
                "provider": "deepseek",
            },
        )
        self.assertNotIn("api_key", data)

    def test_save_project_config_merges_existing_non_secret_values(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-config-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps(
                    {
                        "provider": "minimax",
                        "input_usd_per_million": "0.1",
                        "api_key": "SHOULD_BE_REMOVED",
                        "OPENAI_COMPAT_API_KEY": "SHOULD_ALSO_BE_REMOVED",
                    }
                ),
                encoding="utf-8",
            )

            save_project_config(base, model="MiniMax-custom")
            data = json.loads((config_dir / "config.json").read_text(encoding="utf-8"))

        self.assertEqual(data["provider"], "minimax")
        self.assertEqual(data["model"], "MiniMax-custom")
        self.assertEqual(data["input_usd_per_million"], "0.1")
        self.assertNotIn("api_key", data)
        self.assertNotIn("OPENAI_COMPAT_API_KEY", data)

    def test_save_project_config_provider_change_clears_stale_model_defaults(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-config-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps(
                    {
                        "provider": "deepseek",
                        "model": "deepseek-reasoner",
                        "base_url": "https://deepseek.example",
                        "input_usd_per_million": "0.1",
                    }
                ),
                encoding="utf-8",
            )

            save_project_config(base, provider="minimax")
            data = json.loads((config_dir / "config.json").read_text(encoding="utf-8"))

        self.assertEqual(data["provider"], "minimax")
        self.assertEqual(data["input_usd_per_million"], "0.1")
        self.assertNotIn("model", data)
        self.assertNotIn("base_url", data)

    def test_save_project_config_rejects_invalid_existing_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-config-") as base:
            config_dir = Path(base) / ".vibeagent"
            config_dir.mkdir()
            (config_dir / "config.json").write_text("{bad", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Invalid .vibeagent/config.json"):
                save_project_config(base, provider="deepseek")

    def test_save_project_config_requires_at_least_one_value(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-config-") as base:
            with self.assertRaisesRegex(ValueError, "--save-config requires at least one"):
                save_project_config(base)

    def test_save_project_config_rejects_invalid_execution_defaults(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-config-") as base:
            with self.assertRaisesRegex(ValueError, "command_timeout_ms must be at least 100"):
                save_project_config(base, command_timeout_ms=99)

    def test_model_text_never_exposes_key_values(self) -> None:
        text = get_model_text(
            {
                "VIBEAGENT_PROVIDER": "deepseek",
                "OPENAI_COMPAT_API_KEY": "secret-value",
                "OPENAI_COMPAT_BASE_URL": "https://api.example",
                "OPENAI_COMPAT_MODEL": "custom-model",
            }
        )

        self.assertIn("Model provider: deepseek", text)
        self.assertIn("model: custom-model", text)
        self.assertIn("baseUrl: https://api.example", text)
        self.assertIn("apiKey: configured via OPENAI_COMPAT_API_KEY", text)
        self.assertNotIn("secret-value", text)

    def test_unsupported_provider_is_clear(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported VIBEAGENT_PROVIDER: unknown"):
            resolve_provider_config({"VIBEAGENT_PROVIDER": "unknown"})

        self.assertEqual(
            get_model_text({"VIBEAGENT_PROVIDER": "unknown"}),
            "Unsupported VIBEAGENT_PROVIDER: unknown",
        )

    def test_resolve_cost_rates_reads_non_negative_decimal_env_values(self) -> None:
        rates, errors = resolve_cost_rates(
            {
                "VIBEAGENT_INPUT_USD_PER_MILLION": "0.30",
                "VIBEAGENT_OUTPUT_USD_PER_MILLION": "1.20",
                "VIBEAGENT_CACHE_CREATION_USD_PER_MILLION": "0.10",
                "VIBEAGENT_CACHE_READ_USD_PER_MILLION": "0.03",
            }
        )

        self.assertEqual(errors, [])
        self.assertEqual(rates.input_usd_per_million, Decimal("0.30"))
        self.assertEqual(rates.output_usd_per_million, Decimal("1.20"))
        self.assertEqual(rates.cache_creation_usd_per_million, Decimal("0.10"))
        self.assertEqual(rates.cache_read_usd_per_million, Decimal("0.03"))

    def test_resolve_cost_rates_reports_invalid_values_without_guessing(self) -> None:
        rates, errors = resolve_cost_rates(
            {
                "VIBEAGENT_INPUT_USD_PER_MILLION": "-1",
                "VIBEAGENT_OUTPUT_USD_PER_MILLION": "bad",
            }
        )

        self.assertIsNone(rates.input_usd_per_million)
        self.assertIsNone(rates.output_usd_per_million)
        self.assertEqual(
            errors,
            [
                "VIBEAGENT_INPUT_USD_PER_MILLION must be a non-negative decimal.",
                "VIBEAGENT_OUTPUT_USD_PER_MILLION must be a non-negative decimal.",
            ],
        )


if __name__ == "__main__":
    unittest.main()
