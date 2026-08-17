import unittest

from vibeagent.remote_control_names import (
    MAX_REMOTE_CONTROL_PREFIX_CHARS,
    resolve_remote_control_name,
    validate_remote_control_name_options,
)


class RemoteControlNameTests(unittest.TestCase):
    def test_explicit_name_is_normalized(self) -> None:
        self.assertEqual(
            resolve_remote_control_name("  release   console  ", None),
            "release console",
        )

    def test_auto_name_uses_prefix_or_hostname_and_suffix(self) -> None:
        self.assertEqual(
            resolve_remote_control_name(True, "devbox", suffix="a1b2c3"),
            "devbox-a1b2c3",
        )
        self.assertEqual(
            resolve_remote_control_name(True, None, hostname="host-1", suffix="abcdef"),
            "host-1-abcdef",
        )

    def test_validation_bounds_and_rejects_unsafe_names(self) -> None:
        self.assertIsNone(validate_remote_control_name_options(True, "devbox"))
        self.assertIn(
            "must not exceed",
            validate_remote_control_name_options(
                True,
                "x" * (MAX_REMOTE_CONTROL_PREFIX_CHARS + 1),
            )
            or "",
        )
        self.assertIn(
            "control characters",
            validate_remote_control_name_options("bad\nname", None) or "",
        )


if __name__ == "__main__":
    unittest.main()
