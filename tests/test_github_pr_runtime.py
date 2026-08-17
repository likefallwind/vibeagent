from __future__ import annotations

import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.action_parsing import ActionParseError, parse_tool_action
from vibeagent.agent_approval import build_approval_request
from vibeagent.github_pr_runtime import create_github_pr, parse_github_repository, preview_github_pr_create
from vibeagent.types import CheckGitHubPrCreateAction, GitHubPrCreateAction
from vibeagent.workspace import create_run_workspace


class GitHubPrRuntimeTests(unittest.TestCase):
    def test_parse_github_repository_supports_https_and_ssh(self) -> None:
        self.assertEqual(parse_github_repository("https://github.com/acme/widgets.git"), ("acme", "widgets"))
        self.assertEqual(parse_github_repository("git@github.com:acme/widgets.git"), ("acme", "widgets"))
        self.assertIsNone(parse_github_repository("https://example.com/acme/widgets.git"))

    def test_action_parser_and_approval_preserve_pr_options(self) -> None:
        action = parse_tool_action(
            "github_pr_create",
            {"title": "Ship feature", "body": "Details", "base": "main", "remote": "origin", "draft": True},
        )
        self.assertEqual(
            action,
            GitHubPrCreateAction(
                type="github_pr_create", title="Ship feature", body="Details", base="main", remote="origin", draft=True
            ),
        )
        request = build_approval_request(action)
        self.assertIsNotNone(request)
        self.assertEqual(request.action_type, "github_pr_create")

    def test_action_parser_rejects_multiline_title(self) -> None:
        with self.assertRaises(ActionParseError):
            parse_tool_action("check_github_pr_create", {"title": "bad\ntitle"})

    def test_preflight_and_create_use_a_fully_pushed_branch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project, gh, argv_file = self._project_with_pushed_feature(Path(temp_dir))
            workspace = create_run_workspace(project, run_id="pr-test")
            with patch("vibeagent.github_pr_runtime.shutil.which", return_value=str(gh)):
                preview = preview_github_pr_create(
                    workspace, title="--not-an-option", body="Body", base=None, remote=None, draft=True
                )
                self.assertTrue(preview["ok"], preview["message"])
                self.assertEqual(preview["repository"], "acme/widgets")
                self.assertEqual(preview["head"], "feature")
                self.assertEqual(preview["base"], "main")
                self.assertEqual(preview["commits"], 1)

                result = create_github_pr(
                    workspace, title="--not-an-option", body="Body", base=None, remote=None, draft=True
                )
            self.assertTrue(result["ok"], result["message"])
            self.assertEqual(result["url"], "https://github.com/acme/widgets/pull/42")
            argv = argv_file.read_text(encoding="utf-8").splitlines()
            self.assertEqual(argv[:2], ["pr", "create"])
            self.assertEqual(argv[argv.index("--title") + 1], "--not-an-option")
            self.assertEqual(argv[-1], "--draft")

    def test_preflight_rejects_unpushed_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project, gh, _ = self._project_with_pushed_feature(Path(temp_dir))
            (project / "local.txt").write_text("local\n", encoding="utf-8")
            self._git(project, "add", "local.txt")
            self._git(project, "commit", "-m", "local only")
            workspace = create_run_workspace(project, run_id="unpushed-test")
            with patch("vibeagent.github_pr_runtime.shutil.which", return_value=str(gh)):
                result = preview_github_pr_create(workspace, title="Feature")
            self.assertFalse(result["ok"])
            self.assertEqual(result["ahead"], 1)
            self.assertIn("fetch and push first", result["message"])

    def test_create_finds_url_after_large_cli_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project, gh, _ = self._project_with_pushed_feature(Path(temp_dir))
            gh.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "sys.stdout.write('noise' * 400_000)\n"
                "sys.stdout.write('\\nhttps://github.com/acme/widgets/pull/42\\n')\n",
                encoding="utf-8",
            )
            gh.chmod(0o755)
            workspace = create_run_workspace(project, run_id="large-gh-output")

            with patch("vibeagent.github_pr_runtime.shutil.which", return_value=str(gh)):
                result = create_github_pr(workspace, title="Feature")

        self.assertTrue(result["ok"], result["message"])
        self.assertEqual(result["url"], "https://github.com/acme/widgets/pull/42")

    def test_preflight_rejects_non_github_remote(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project, gh, _ = self._project_with_pushed_feature(Path(temp_dir))
            self._git(project, "remote", "set-url", "origin", "https://example.com/acme/widgets.git")
            workspace = create_run_workspace(project, run_id="remote-test")
            with patch("vibeagent.github_pr_runtime.shutil.which", return_value=str(gh)):
                result = preview_github_pr_create(workspace, title="Feature")
            self.assertFalse(result["ok"])
            self.assertIn("not a GitHub repository", result["message"])

    def test_preflight_formats_fork_head_for_an_upstream_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project, gh, _ = self._project_with_pushed_feature(Path(temp_dir))
            self._git(project, "remote", "add", "upstream", "https://github.com/platform/widgets.git")
            self._git(project, "update-ref", "refs/remotes/upstream/main", "refs/remotes/origin/main")
            workspace = create_run_workspace(project, run_id="fork-test")
            with patch("vibeagent.github_pr_runtime.shutil.which", return_value=str(gh)):
                result = preview_github_pr_create(
                    workspace, title="Feature", base="main", remote="upstream"
                )
            self.assertTrue(result["ok"], result["message"])
            self.assertEqual(result["repository"], "platform/widgets")
            self.assertEqual(result["head"], "acme:feature")

    def _project_with_pushed_feature(self, root: Path) -> tuple[Path, Path, Path]:
        bare = root / "remote.git"
        project = root / "project"
        self._git(root, "init", "--bare", str(bare))
        self._git(root, "init", "--initial-branch=main", str(project))
        self._git(project, "config", "user.name", "Test User")
        self._git(project, "config", "user.email", "test@example.com")
        (project / "README.md").write_text("base\n", encoding="utf-8")
        self._git(project, "add", "README.md")
        self._git(project, "commit", "-m", "base")
        self._git(project, "remote", "add", "origin", str(bare))
        self._git(project, "push", "-u", "origin", "main")
        self._git(project, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        self._git(project, "switch", "-c", "feature")
        (project / "feature.txt").write_text("feature\n", encoding="utf-8")
        self._git(project, "add", "feature.txt")
        self._git(project, "commit", "-m", "feature")
        self._git(project, "push", "-u", "origin", "feature")
        self._git(project, "remote", "set-url", "origin", "git@github.com:acme/widgets.git")

        argv_file = root / "gh-argv.txt"
        gh = root / "gh"
        gh.write_text(
            "#!/bin/sh\n"
            f"printf '%s\\n' \"$@\" > {shlex.quote(str(argv_file))}\n"
            "printf '%s\\n' 'https://github.com/acme/widgets/pull/42'\n",
            encoding="utf-8",
        )
        gh.chmod(0o755)
        return project, gh, argv_file

    def _git(self, cwd: Path, *args: str) -> None:
        subprocess.run(["git", *args], cwd=cwd, check=True, text=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
