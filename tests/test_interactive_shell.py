from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent.interactive_shell import parse_shell_mode_input, run_interactive_shell
from vibeagent.session import build_session_resume_context, read_session_events


class InteractiveShellTests(unittest.TestCase):
    def test_parse_shell_mode_input(self) -> None:
        self.assertEqual(parse_shell_mode_input("! pytest -q"), "pytest -q")
        self.assertEqual(parse_shell_mode_input("!pytest -q"), "pytest -q")
        self.assertEqual(parse_shell_mode_input("!   "), "")
        self.assertIsNone(parse_shell_mode_input("explain !important"))

    def test_command_result_is_recorded_for_resume_and_redacted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-shell-") as base:
            first = run_interactive_shell(
                base,
                "printf 'OPENAI_API_KEY=plain-secret'",
            )
            second = run_interactive_shell(
                base,
                "printf second-command",
                run_id=first.run_id,
            )
            events = read_session_events(base, first.run_id)
            context = build_session_resume_context(base, first.run_id)

        self.assertEqual(first.text, "OPENAI_API_KEY=plain-secret")
        self.assertEqual(second.run_id, first.run_id)
        self.assertEqual(second.text, "second-command")
        self.assertEqual([event.type for event in events], ["tool_call", "tool_result", "tool_call", "tool_result"])
        self.assertTrue(all(event.payload.get("source") == "interactive_shell" for event in events))
        self.assertEqual([event.payload.get("name") for event in events], ["Bash"] * 4)
        self.assertIn("printf second-command", context)
        self.assertIn("second-command", context)
        self.assertIn("OPENAI_API_KEY=[REDACTED]", context)
        self.assertNotIn("plain-secret", context)

    def test_hard_block_and_session_symlink_refusal_remain_enforced(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-shell-") as base:
            root = Path(base)
            blocked = run_interactive_shell(root, "sudo reboot")
            outside = root / "outside"
            outside.mkdir()
            linked = root / ".vibeagent" / "sessions" / "linked"
            linked.symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "Session path is not a regular directory"):
                run_interactive_shell(root, "printf unsafe", run_id="linked")

            safe = run_interactive_shell(root, "printf initial")
            events_path = root / ".vibeagent" / "sessions" / safe.run_id / "events.jsonl"
            events_path.unlink()
            outside_events = root / "outside-events.jsonl"
            outside_events.write_text("outside\n", encoding="utf-8")
            events_path.symlink_to(outside_events)
            marker = root / "must-not-exist"
            with self.assertRaisesRegex(ValueError, "Session events path is not a regular file"):
                run_interactive_shell(root, f"printf unsafe > {marker.name}", run_id=safe.run_id)

        self.assertIsNone(blocked.result.exit_code)
        self.assertIn("Command blocked:", blocked.text)
        self.assertIn("[command not run]", blocked.text)
        self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
