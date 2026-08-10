from __future__ import annotations

import unittest

from vibeagent.verification_command_utils import matching_verification_command_key


class VerificationCommandUtilsTests(unittest.TestCase):
    def test_python_no_bytecode_flag_matches_recorded_check(self) -> None:
        expected = ("python -m unittest discover -s tests", ".")

        self.assertEqual(
            matching_verification_command_key(
                "python -B -m unittest discover -s tests",
                ".",
                {expected},
            ),
            expected,
        )

    def test_semantic_python_flags_do_not_match_recorded_check(self) -> None:
        expected = ("python -m unittest discover -s tests", ".")

        self.assertIsNone(
            matching_verification_command_key(
                "python -O -m unittest discover -s tests",
                ".",
                {expected},
            )
        )

    def test_equivalent_command_still_requires_same_working_directory(self) -> None:
        expected = ("python -m unittest discover -s tests", "server")

        self.assertIsNone(
            matching_verification_command_key(
                "python -B -m unittest discover -s tests",
                ".",
                {expected},
            )
        )


if __name__ == "__main__":
    unittest.main()
