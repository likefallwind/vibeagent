import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent import cli as cli_module
from vibeagent.cli_worktree import create_cli_worktree


def init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
    (root / "app.py").write_text("value = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)


class CliWorktreeTests(unittest.TestCase):
    def test_args_accept_worktree_and_native_anthropic_provider(self) -> None:
        args = cli_module.parse_args(
            ["--cwd", "/tmp/project", "--worktree", "feature", "--provider", "anthropic", "inspect"]
        )
        short = cli_module.parse_args(["-w", "short-name", "inspect"])
        generated = cli_module.parse_args(["--worktree", "--", "inspect"])

        self.assertEqual(args.worktree, "feature")
        self.assertEqual(args.provider, "anthropic")
        self.assertEqual(args.task, ["inspect"])
        self.assertEqual(short.worktree, "short-name")
        self.assertEqual(generated.worktree, "")
        self.assertEqual(generated.task, ["inspect"])

    def test_validation_limits_worktree_to_fresh_coding_sessions(self) -> None:
        local = cli_module.parse_args(["--worktree", "feature", "--tools"])
        chat = cli_module.parse_args(["--worktree", "feature", "--chat", "hello"])
        resume = cli_module.parse_args(["--worktree", "feature", "--resume", "run-1", "continue"])

        self.assertEqual(
            cli_module.validate_cli_args(local),
            "--worktree requires an interactive or one-shot coding session.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(chat),
            "--worktree requires an interactive or one-shot coding session.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(resume),
            "--worktree cannot be combined with --resume, --session-id, --compact, or --continue.",
        )

    def test_helper_creates_isolated_branch_and_copies_only_safe_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-worktree-") as base:
            root = Path(base)
            init_git_repo(root)
            (root / ".vibeagent").mkdir()
            (root / ".vibeagent" / "config.json").write_text(
                json.dumps(
                    {
                        "provider": "anthropic",
                        "model": "claude-sonnet-5",
                        "max_iterations": 12,
                        "ANTHROPIC_API_KEY": "must-not-copy",
                    }
                ),
                encoding="utf-8",
            )
            created = create_cli_worktree(root, "feature")
            copied = json.loads((created.root / ".vibeagent" / "config.json").read_text(encoding="utf-8"))

        self.assertEqual(created.branch, "vibeagent/feature")
        self.assertEqual(created.root, root / ".vibeagent" / "worktrees" / "feature")
        self.assertEqual(copied["provider"], "anthropic")
        self.assertEqual(copied["model"], "claude-sonnet-5")
        self.assertEqual(copied["max_iterations"], 12)
        self.assertNotIn("ANTHROPIC_API_KEY", copied)

    def test_invalid_config_fails_before_creating_worktree(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-worktree-") as base:
            root = Path(base)
            init_git_repo(root)
            (root / ".vibeagent").mkdir()
            (root / ".vibeagent" / "config.json").write_text("{bad", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Invalid .vibeagent/config.json"):
                create_cli_worktree(root, "invalid-config")

            self.assertFalse((root / ".vibeagent" / "worktrees" / "invalid-config").exists())
            branches = subprocess.run(
                ["git", "branch", "--format=%(refname:short)"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
            self.assertNotIn("vibeagent/invalid-config", branches)

    def test_main_routes_one_shot_execution_into_isolated_root(self) -> None:
        captured: dict[str, object] = {}

        def fake_run_one_shot(**kwargs) -> int:
            captured.update(kwargs)
            project_root = Path(str(kwargs["base_dir"]))
            (project_root / "app.py").write_text("value = 2\n", encoding="utf-8")
            return 0

        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-worktree-") as base:
            root = Path(base)
            init_git_repo(root)
            with patch.object(cli_module, "run_one_shot", side_effect=fake_run_one_shot):
                exit_code = cli_module.main(["--cwd", str(root), "--worktree", "one-shot", "modify", "app"])
            linked_root = Path(str(captured["base_dir"]))
            main_content = (root / "app.py").read_text(encoding="utf-8")
            linked_content = (linked_root / "app.py").read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertEqual(captured["task"], "modify app")
        self.assertEqual(linked_root, root / ".vibeagent" / "worktrees" / "one-shot")
        self.assertEqual(main_content, "value = 1\n")
        self.assertEqual(linked_content, "value = 2\n")

    def test_main_routes_interactive_session_into_isolated_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-worktree-") as base:
            root = Path(base)
            init_git_repo(root)
            with patch.object(cli_module, "run_interactive", return_value=0) as run_interactive:
                exit_code = cli_module.main(["--cwd", str(root), "--worktree", "interactive"])

        self.assertEqual(exit_code, 0)
        isolated_root = root / ".vibeagent" / "worktrees" / "interactive"
        run_interactive.assert_called_once()
        self.assertEqual(Path(run_interactive.call_args.args[0]), isolated_root)

    def test_non_git_worktree_failure_uses_json_error_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-worktree-") as base:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = cli_module.main(
                    ["--json", "--cwd", base, "--worktree", "feature", "inspect"]
                )
            payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 2)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], "failed")
        self.assertIn("not a git repository", payload["error"])


if __name__ == "__main__":
    unittest.main()
