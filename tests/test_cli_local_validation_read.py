import unittest

from vibeagent.cli import parse_args
from vibeagent.cli_local_option_validation import validate_local_option_dependencies
from vibeagent.cli_local_validation_read import (
    validate_code_intel_option_dependencies,
    validate_read_discovery_option_dependencies,
)


class CliLocalValidationReadTests(unittest.TestCase):
    def test_read_discovery_helper_reports_existing_errors(self) -> None:
        args = parse_args(["--read-lines", "2:4", "fix", "tests"])

        self.assertEqual(
            validate_read_discovery_option_dependencies(args),
            "--read-lines can only be used with --read.",
        )
        self.assertEqual(validate_local_option_dependencies(args), "--read-lines can only be used with --read.")

    def test_code_intel_helper_reports_existing_errors(self) -> None:
        args = parse_args(["--code-max-matches", "3", "fix", "tests"])

        self.assertEqual(
            validate_code_intel_option_dependencies(args),
            "--code-max-matches can only be used with --code-refs, --code-ref-contexts, or --code-defs.",
        )
        self.assertEqual(
            validate_local_option_dependencies(args),
            "--code-max-matches can only be used with --code-refs, --code-ref-contexts, or --code-defs.",
        )


if __name__ == "__main__":
    unittest.main()
