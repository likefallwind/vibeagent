from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.test_project_agents import _write_agent
from vibeagent.agent_delegate_profile import load_delegate_profile_runtime
from vibeagent.cli_project_command_expansion import expand_one_shot_project_command
from vibeagent.types import DelegateTaskAction
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_prompt_commands import (
    expand_project_prompt_command,
    read_project_prompt_commands,
)
from vibeagent.workspace_skills import read_project_skill, read_project_skills


def _write_skill(root: Path, base: str, name: str, body: str) -> Path:
    path = root / base / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {name}\ndescription: {name} instructions\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return path


def _write_command(root: Path, base: str, name: str, body: str) -> Path:
    path = root / base / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ndescription: {name} command\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return path


class UserSkillTests(unittest.TestCase):
    def test_user_skill_is_available_across_projects_and_overrides_project_skill(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-skills-") as base:
            root = Path(base)
            home = root / "home"
            project_a = root / "project-a"
            project_b = root / "project-b"
            home.mkdir()
            project_a.mkdir()
            project_b.mkdir()
            _write_skill(home, ".claude/skills", "review", "USER_REVIEW_SKILL")
            _write_skill(project_b, ".claude/skills", "review", "PROJECT_REVIEW_SKILL")

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                catalog_a = read_project_skills(create_run_workspace(project_a, "skills-a"))
                workspace_b = create_run_workspace(project_b, "skills-b")
                catalog_b = read_project_skills(workspace_b)
                loaded_b = read_project_skill(workspace_b, "review")

        self.assertEqual(catalog_a["total"], 1)
        self.assertEqual(catalog_a["skills"][0]["source"], "user")
        self.assertTrue(str(catalog_a["skills"][0]["path"]).startswith(str(home)))
        self.assertEqual(catalog_b["total"], 1)
        self.assertEqual(catalog_b["skills"][0]["source"], "user")
        self.assertIn("USER_REVIEW_SKILL", str(loaded_b["content"]))
        self.assertNotIn("PROJECT_REVIEW_SKILL", str(loaded_b["content"]))

    def test_user_skill_symlink_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-skills-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            outside = root / "outside.md"
            outside.write_text(
                "---\nname: linked\ndescription: linked instructions\n---\n\nSECRET\n",
                encoding="utf-8",
            )
            linked = home / ".claude/skills/linked/SKILL.md"
            linked.parent.mkdir(parents=True)
            linked.symlink_to(outside)

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                catalog = read_project_skills(create_run_workspace(project, "linked-skill"))

        self.assertEqual(catalog["total"], 1)
        self.assertFalse(catalog["skills"][0]["available"])
        self.assertIn("symbolic link", str(catalog["skills"][0]["message"]))

    def test_user_agent_preloads_user_skill(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-skills-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            _write_skill(home, ".claude/skills", "personal-review", "USER_PRELOADED_SKILL")
            _write_agent(
                home,
                ".claude/agents",
                "personal-reviewer",
                "Personal reviewer",
                "USER_AGENT_PROMPT",
                skills="personal-review",
            )

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                runtime = load_delegate_profile_runtime(
                    create_run_workspace(project, "user-agent-skill"),
                    DelegateTaskAction(
                        type="delegate_task",
                        task="Review this project",
                        agent="personal-reviewer",
                    ),
                )

        self.assertIsNone(runtime.error)
        self.assertEqual(runtime.skills, ("personal-review",))
        self.assertIn("USER_AGENT_PROMPT", runtime.prompt or "")
        self.assertIn("USER_PRELOADED_SKILL", runtime.prompt or "")


class UserPromptCommandTests(unittest.TestCase):
    def test_user_command_is_available_across_projects_and_overrides_project_command(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-commands-") as base:
            root = Path(base)
            home = root / "home"
            project_a = root / "project-a"
            project_b = root / "project-b"
            home.mkdir()
            project_a.mkdir()
            project_b.mkdir()
            _write_command(home, ".claude/commands", "fix", "USER_FIX $1")
            _write_command(project_b, ".claude/commands", "fix", "PROJECT_FIX $1")

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                report_a = read_project_prompt_commands(project_a)
                report_b = read_project_prompt_commands(project_b)
                expanded_b = expand_project_prompt_command(project_b, "/fix login")

        self.assertEqual(report_a["total"], 1)
        self.assertEqual(report_a["commands"][0]["source"], "user")
        self.assertTrue(str(report_a["commands"][0]["path"]).startswith(str(home)))
        self.assertEqual(report_b["total"], 1)
        self.assertEqual(report_b["commands"][0]["source"], "user")
        self.assertEqual(expanded_b["prompt"], "USER_FIX login")

    def test_user_command_symlink_and_builtin_conflict_are_unavailable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-commands-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            outside = root / "outside.md"
            outside.write_text("EXTERNAL", encoding="utf-8")
            linked = home / ".claude/commands/linked.md"
            linked.parent.mkdir(parents=True)
            linked.symlink_to(outside)
            _write_command(home, ".claude/commands", "help", "REPLACE_HELP")

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                report = read_project_prompt_commands(project)

        messages = {str(item["name"]): str(item["message"]) for item in report["commands"]}
        self.assertIn("built-in command", messages["help"])
        self.assertIn("symbolic link", messages["linked"])
        self.assertEqual(report["invalid"], 2)

    def test_skill_invocation_takes_precedence_over_legacy_command(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-commands-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            _write_skill(home, ".claude/skills", "personal-review", "SKILL_REVIEW $ARGUMENTS")
            _write_command(home, ".claude/commands", "personal-review", "COMMAND_REVIEW $ARGUMENTS")

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                report = read_project_prompt_commands(project)
                task, metadata = expand_one_shot_project_command(project, "/personal-review src/app.py")

        self.assertEqual(report["total"], 1)
        self.assertFalse(report["commands"][0]["available"])
        self.assertIn("shadowed by a skill", str(report["commands"][0]["message"]))
        self.assertEqual(task, "SKILL_REVIEW src/app.py")
        self.assertEqual(
            metadata,
            {
                "source": "custom_skill",
                "name": "personal-review",
                "path": str(home / ".claude/skills/personal-review/SKILL.md"),
                "arguments": "src/app.py",
            },
        )


if __name__ == "__main__":
    unittest.main()
