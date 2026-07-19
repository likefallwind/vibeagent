from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent import workspace_review_tests
from vibeagent.workspace_focused_test_commands import (
    add_focused_test_commands_for_file,
    focused_npm_test_command,
    nearest_package_json,
    preferred_test_script_name,
    project_has_pytest_evidence,
)


class WorkspaceFocusedTestCommandsTests(unittest.TestCase):
    def test_review_tests_reexports_focused_command_helpers(self) -> None:
        self.assertIs(
            workspace_review_tests.add_focused_test_commands_for_file,
            add_focused_test_commands_for_file,
        )
        self.assertIs(
            workspace_review_tests.focused_npm_test_command,
            focused_npm_test_command,
        )
        self.assertIs(workspace_review_tests.nearest_package_json, nearest_package_json)
        self.assertIs(
            workspace_review_tests.preferred_test_script_name,
            preferred_test_script_name,
        )
        self.assertIs(
            workspace_review_tests.project_has_pytest_evidence,
            project_has_pytest_evidence,
        )

    def test_add_focused_python_commands_includes_pytest_when_evidence_exists(self) -> None:
        commands: list[dict[str, object]] = []

        add_focused_test_commands_for_file(
            commands,
            Path("."),
            ["pytest.ini", "tests/test_app.py"],
            "tests/test_app.py",
            source="src/app.py",
            candidate_reason="Related.",
            pytest_evidence=True,
        )

        self.assertEqual(
            [item["command"] for item in commands],
            [
                "python -m pytest tests/test_app.py",
                "python -m unittest discover -s tests -p test_app.py",
            ],
        )

    def test_focused_npm_test_command_prefers_nearest_package_script(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-focused-npm-") as tmp:
            root = Path(tmp)
            package_dir = root / "web"
            package_dir.mkdir()
            (package_dir / "package.json").write_text(
                '{"scripts": {"test:unit": "vitest"}}',
                encoding="utf-8",
            )

            self.assertEqual(
                focused_npm_test_command(
                    root,
                    ["web/package.json", "web/src/app.test.ts"],
                    "web/src/app.test.ts",
                ),
                ("npm run test:unit -- src/app.test.ts", "web"),
            )

    def test_project_has_pytest_evidence_reads_common_config_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-pytest-evidence-") as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[tool.pytest.ini_options]\naddopts = "-q"\n',
                encoding="utf-8",
            )
            (root / "setup.cfg").write_text("[metadata]\nname = demo\n", encoding="utf-8")

            self.assertTrue(project_has_pytest_evidence(root, ["pyproject.toml"]))
            self.assertFalse(project_has_pytest_evidence(root, ["setup.cfg"]))


if __name__ == "__main__":
    unittest.main()
