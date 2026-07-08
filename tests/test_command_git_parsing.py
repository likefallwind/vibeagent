import unittest

from vibeagent.command_git_parsing import parse_git_local_command
from vibeagent.command_parsing import LocalCommand, parse_local_command


class CommandGitParsingTests(unittest.TestCase):
    def test_git_parser_recognizes_git_commands(self) -> None:
        cases = {
            "/git-status": LocalCommand(type="git_status"),
            "/conflicts src": LocalCommand(type="git_conflicts", argument="src"),
            "/git-info": LocalCommand(type="git_info"),
            "/branches": LocalCommand(type="branches"),
            "/log": LocalCommand(type="log"),
            "/log app.py 2": LocalCommand(type="log", argument="app.py 2"),
            "/show": LocalCommand(type="show"),
            "/show HEAD app.py": LocalCommand(type="show", argument="HEAD app.py"),
            "/blame app.py 2:2": LocalCommand(type="blame", argument="app.py 2:2"),
            "/blame": LocalCommand(type="blame"),
            "/stashes": LocalCommand(type="stashes"),
            "/stashes 5": LocalCommand(type="stashes", argument="5"),
            "/check-fetch origin": LocalCommand(type="check_fetch", argument="origin"),
            "/check-fetch": LocalCommand(type="check_fetch"),
            "/fetch origin": LocalCommand(type="fetch", argument="origin"),
            "/fetch": LocalCommand(type="fetch"),
            "/check-pull": LocalCommand(type="check_pull"),
            "/pull": LocalCommand(type="pull"),
            "/check-push": LocalCommand(type="check_push"),
            "/push": LocalCommand(type="push"),
            "/check-stash --include-untracked save work": LocalCommand(type="check_stash", argument="--include-untracked save work"),
            "/check-stash": LocalCommand(type="check_stash"),
            "/stash save work": LocalCommand(type="stash", argument="save work"),
            "/stash": LocalCommand(type="stash"),
            "/check-stash-apply stash@{0}": LocalCommand(type="check_stash_apply", argument="stash@{0}"),
            "/check-stash-apply": LocalCommand(type="check_stash_apply"),
            "/stash-apply stash@{0}": LocalCommand(type="stash_apply", argument="stash@{0}"),
            "/stash-apply": LocalCommand(type="stash_apply"),
            "/check-stash-drop stash@{0}": LocalCommand(type="check_stash_drop", argument="stash@{0}"),
            "/check-stash-drop": LocalCommand(type="check_stash_drop"),
            "/stash-drop stash@{0}": LocalCommand(type="stash_drop", argument="stash@{0}"),
            "/stash-drop": LocalCommand(type="stash_drop"),
            "/check-stage app.py tests/test_app.py": LocalCommand(type="check_stage", argument="app.py tests/test_app.py"),
            "/check-stage": LocalCommand(type="check_stage"),
            "/stage app.py": LocalCommand(type="stage", argument="app.py"),
            "/stage": LocalCommand(type="stage"),
            "/check-unstage app.py tests/test_app.py": LocalCommand(type="check_unstage", argument="app.py tests/test_app.py"),
            "/check-unstage": LocalCommand(type="check_unstage"),
            "/unstage app.py": LocalCommand(type="unstage", argument="app.py"),
            "/unstage": LocalCommand(type="unstage"),
            "/check-commit update app": LocalCommand(type="check_commit", argument="update app"),
            "/check-commit": LocalCommand(type="check_commit"),
            "/commit update app": LocalCommand(type="commit", argument="update app"),
            "/commit": LocalCommand(type="commit"),
            "/check-restore app.py tests/test_app.py": LocalCommand(type="check_restore", argument="app.py tests/test_app.py"),
            "/check-restore": LocalCommand(type="check_restore"),
            "/restore app.py": LocalCommand(type="restore", argument="app.py"),
            "/restore": LocalCommand(type="restore"),
            "/check-switch --create feature/demo": LocalCommand(type="check_switch", argument="--create feature/demo"),
            "/check-switch": LocalCommand(type="check_switch"),
            "/switch feature/demo": LocalCommand(type="switch", argument="feature/demo"),
            "/switch": LocalCommand(type="switch"),
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_git_local_command(raw), expected)
                self.assertEqual(parse_local_command(raw), expected)

    def test_git_parser_ignores_other_commands(self) -> None:
        self.assertIsNone(parse_git_local_command("/session run-1"))
        self.assertIsNone(parse_git_local_command("git-status"))


if __name__ == "__main__":
    unittest.main()
