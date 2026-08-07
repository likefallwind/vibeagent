import unittest

from vibeagent import config
from vibeagent import config_validation


class ConfigValidationTests(unittest.TestCase):
    def test_config_reexports_validation_helpers(self) -> None:
        names = [
            "parse_int_config",
            "validate_positive_int",
            "validate_nonnegative_int",
            "validate_timeout_ms",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(config, name), getattr(config_validation, name))

    def test_validation_helpers_keep_existing_behavior(self) -> None:
        self.assertEqual(config_validation.parse_int_config("42", "max_iterations"), 42)
        self.assertEqual(config_validation.validate_positive_int(1, "max_iterations"), 1)
        self.assertEqual(config_validation.validate_nonnegative_int(0, "model_retries"), 0)
        self.assertEqual(config_validation.validate_timeout_ms("100", "command_timeout_ms"), 100)

        with self.assertRaisesRegex(ValueError, "max_iterations must be a positive integer"):
            config_validation.validate_positive_int(0, "max_iterations")
        with self.assertRaisesRegex(ValueError, "model_retries must be a non-negative integer"):
            config_validation.validate_nonnegative_int(-1, "model_retries")
        with self.assertRaisesRegex(ValueError, "command_timeout_ms must be at least 100"):
            config_validation.validate_timeout_ms(99, "command_timeout_ms")


if __name__ == "__main__":
    unittest.main()
