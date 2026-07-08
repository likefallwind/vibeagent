import unittest

from vibeagent.command_checkpoint_parsing import parse_checkpoint_local_command
from vibeagent.command_parsing import LocalCommand, parse_local_command


def make_local_command(command_type: str, argument: str | None = None) -> LocalCommand:
    return LocalCommand(type=command_type, argument=argument)  # type: ignore[arg-type]


class CommandCheckpointParsingTests(unittest.TestCase):
    def test_checkpoint_parser_recognizes_checkpoint_commands(self) -> None:
        cases = {
            "/checkpoint": LocalCommand(type="checkpoint"),
            "/checkpoint before refactor": LocalCommand(type="checkpoint", argument="before refactor"),
            "/checkpoints": LocalCommand(type="checkpoints"),
            "/checkpoint-show ckpt-1": LocalCommand(type="checkpoint_show", argument="ckpt-1"),
            "/checkpoint-diff ckpt-1": LocalCommand(type="checkpoint_diff", argument="ckpt-1"),
            "/checkpoint-status ckpt-1": LocalCommand(type="checkpoint_status", argument="ckpt-1"),
            "/check-checkpoint-restore ckpt-1": LocalCommand(type="check_checkpoint_restore", argument="ckpt-1"),
            "/checkpoint-restore ckpt-1": LocalCommand(type="checkpoint_restore", argument="ckpt-1"),
            "/check-checkpoint-delete ckpt-1": LocalCommand(type="check_checkpoint_delete", argument="ckpt-1"),
            "/checkpoint-delete ckpt-1": LocalCommand(type="checkpoint_delete", argument="ckpt-1"),
            "/check-checkpoint-prune 2": LocalCommand(type="check_checkpoint_prune", argument="2"),
            "/checkpoint-prune 2": LocalCommand(type="checkpoint_prune", argument="2"),
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_checkpoint_local_command(raw, make_local_command), expected)
                self.assertEqual(parse_local_command(raw), expected)

    def test_checkpoint_parser_ignores_other_commands(self) -> None:
        self.assertIsNone(parse_checkpoint_local_command("/session run-1", make_local_command))
        self.assertIsNone(parse_checkpoint_local_command("checkpoint", make_local_command))


if __name__ == "__main__":
    unittest.main()
