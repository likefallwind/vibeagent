import io
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent import cli as cli_module
from vibeagent.cli_tmux import launch_tmux_worktree_session
from vibeagent.cli_worktree import CliWorktree, create_cli_worktree


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

    def test_args_accept_bare_and_classic_tmux_without_consuming_task(self) -> None:
        automatic = cli_module.parse_args(["--worktree", "feature", "--tmux", "inspect"])
        classic = cli_module.parse_args(["--worktree", "feature", "--tmux=classic", "inspect"])
        task_flag = cli_module.parse_args(["--worktree", "--", "--tmux"])

        self.assertEqual(automatic.tmux, "auto")
        self.assertEqual(automatic.task, ["inspect"])
        self.assertEqual(classic.tmux, "classic")
        self.assertEqual(classic.task, ["inspect"])
        self.assertIsNone(task_flag.tmux)
        self.assertEqual(task_flag.task, ["--tmux"])

    def test_tmux_validation_requires_worktree_and_attached_text_mode(self) -> None:
        missing_worktree = cli_module.parse_args(["--tmux", "inspect"])
        print_mode = cli_module.parse_args(
            ["--worktree", "feature", "--tmux", "--print", "inspect"]
        )
        json_mode = cli_module.parse_args(
            ["--worktree", "feature", "--tmux", "--json", "inspect"]
        )

        self.assertEqual(
            cli_module.validate_cli_args(missing_worktree),
            "--tmux requires --worktree.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(print_mode),
            "--tmux requires an attached interactive or one-shot coding session.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(json_mode),
            "--tmux requires text output.",
        )

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

    def test_helper_copies_gitignored_worktree_include_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-worktree-") as base:
            root = Path(base)
            init_git_repo(root)
            root.joinpath(".gitignore").write_text(".env\n.vibeagent/\n", encoding="utf-8")
            root.joinpath(".worktreeinclude").write_text(".env\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", ".gitignore", ".worktreeinclude"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-qm", "configure worktree include"],
                cwd=root,
                check=True,
            )
            root.joinpath(".env").write_text("LOCAL_ONLY=1\n", encoding="utf-8")

            created = create_cli_worktree(root, "with-env")

            self.assertEqual(
                created.root.joinpath(".env").read_text(encoding="utf-8"),
                "LOCAL_ONLY=1\n",
            )

    def test_invalid_worktree_include_removes_created_worktree_and_branch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-worktree-") as base:
            root = Path(base)
            init_git_repo(root)
            root.joinpath("include.txt").write_text(".env\n", encoding="utf-8")
            root.joinpath(".worktreeinclude").symlink_to("include.txt")

            with self.assertRaisesRegex(ValueError, "regular non-symlink"):
                create_cli_worktree(root, "bad-include")

            self.assertFalse(root.joinpath(".vibeagent", "worktrees", "bad-include").exists())
            branches = subprocess.run(
                ["git", "branch", "--format=%(refname:short)"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
            self.assertNotIn("vibeagent/bad-include", branches)

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
                exit_code = cli_module.main(
                    [
                        "--cwd",
                        str(root),
                        "--worktree",
                        "one-shot",
                        "modify",
                        "app",
                        "--file",
                        "file_alpha:fixtures/input.bin",
                    ]
                )
            linked_root = Path(str(captured["base_dir"]))
            main_content = (root / "app.py").read_text(encoding="utf-8")
            linked_content = (linked_root / "app.py").read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertEqual(captured["task"], "modify app")
        self.assertEqual(captured["file_resources"], ("file_alpha:fixtures/input.bin",))
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

    def test_main_routes_created_worktree_to_tmux(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-worktree-") as base:
            root = Path(base)
            init_git_repo(root)
            with (
                patch.object(cli_module, "ensure_tmux_available") as ensure_tmux,
                patch.object(
                    cli_module,
                    "launch_tmux_worktree_session",
                    return_value=7,
                ) as launch,
            ):
                exit_code = cli_module.main(
                    ["--cwd", str(root), "--worktree", "terminal", "--tmux", "inspect"]
                )

        self.assertEqual(exit_code, 7)
        ensure_tmux.assert_called_once_with()
        self.assertEqual(launch.call_args.kwargs["mode"], "auto")
        self.assertEqual(launch.call_args.args[1].name, "terminal")

    def test_missing_tmux_fails_before_worktree_creation(self) -> None:
        with io.StringIO() as stdout, redirect_stdout(stdout):
            with (
                patch.object(
                    cli_module,
                    "ensure_tmux_available",
                    side_effect=ValueError("tmux missing"),
                ),
                patch.object(cli_module, "create_cli_worktree") as create_worktree,
            ):
                exit_code = cli_module.main(["--worktree", "terminal", "--tmux"])

        self.assertEqual(exit_code, 2)
        create_worktree.assert_not_called()

    def test_tmux_launcher_reenters_worktree_without_recursive_flags(self) -> None:
        worktree = CliWorktree(
            source_root=Path("/repo"),
            root=Path("/repo/.vibeagent/worktrees/feature"),
            branch="vibeagent/feature",
            name="feature/name",
        )
        with patch("vibeagent.cli_tmux.subprocess.run") as run:
            run.return_value.returncode = 0
            exit_code = launch_tmux_worktree_session(
                [
                    "--cwd",
                    "/repo",
                    "--worktree",
                    "feature",
                    "--tmux=classic",
                    "--",
                    "inspect",
                    "--tmux",
                ],
                worktree,
                mode="classic",
                environ={"TERM_PROGRAM": "iTerm.app"},
            )

        self.assertEqual(exit_code, 0)
        command = run.call_args.args[0]
        self.assertEqual(command[:6], [
            "tmux",
            "new-session",
            "-s",
            "vibeagent-feature-name",
            "-c",
            str(worktree.root),
        ])
        self.assertEqual(len(command), 7)
        self.assertEqual(
            shlex.split(command[-1]),
            [
                sys.executable,
                "-m",
                "vibeagent",
                "--cwd",
                str(worktree.root),
                "--",
                "inspect",
                "--tmux",
            ],
        )
        self.assertNotIn("--tmux=classic", command[-1])
        run.assert_called_once_with(command, cwd=worktree.root, check=False)

    def test_tmux_auto_mode_uses_iterm_control_mode(self) -> None:
        worktree = CliWorktree(
            source_root=Path("/repo"),
            root=Path("/repo/.vibeagent/worktrees/feature"),
            branch="vibeagent/feature",
            name="feature",
        )
        with patch("vibeagent.cli_tmux.subprocess.run") as run:
            run.return_value.returncode = 0
            launch_tmux_worktree_session(
                ["--worktree=feature", "--tmux"],
                worktree,
                mode="auto",
                environ={"TERM_PROGRAM": "iTerm.app"},
            )

        self.assertEqual(run.call_args.args[0][:3], ["tmux", "-CC", "new-session"])

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
